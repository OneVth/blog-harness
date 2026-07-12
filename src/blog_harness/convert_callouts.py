"""Obsidian callout → Tistory 발행용 HTML 변환기 — guides/RULES.md CONV-01~06.

파이프라인의 마지막 빌드 스텝(`make build`)이다. 초안은 Obsidian callout 문법으로
쓰고, 발행본 HTML 은 여기서 결정론적으로 빌드한다. LLM 이 손으로 하지 않는다.

**왜 필요한가** (실측 2026-07-11): Tistory 는 `<blockquote>` 안의 마크다운을 파싱하지
않는다. callout 본문의 백틱을 그대로 두면 리터럴로 노출된다. 하지만 `<code>` 태그는
스킨이 정상 렌더한다. 그래서 변환기가 본문의 인라인 마크다운을 미리 HTML 로 바꿔놓아야
한다 (CONV-02). callout **밖**의 마크다운(`###`, `**굵게**`, `[링크]`, 이미지)은
Tistory 가 GFM 으로 처리하므로 그대로 남긴다.

설계 경계:
  - **명세 표는 문서에서 파싱한다** — 8종 기본 타이틀(§3)·27개 alias(§4)를 callouts.md
    에서 읽는다. 코드에 상수로 박지 않는다 (AGENTS.md 원칙). 파싱 실패는 SpecError.
  - LaTeX($...$)·인라인 코드는 인라인 변환 전에 placeholder 로 마스킹한다 (CONV-03).
    수식 안의 `*` 가 `<em>` 으로, 코드 안의 `*`/`[` 가 다른 태그로 오인되면 안 된다.
  - 코드 펜스 안은 변환하지 않는다 (CONV-01) — 놓치면 조용히 데이터가 깨진다.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# ── 수준 매핑 ──────────────────────────────────────────────────────────────
# guides/RULES.md § "수준" 과 동기화할 것
WARN = "WARN"
INFO = "INFO"

# ── 정규식 ─────────────────────────────────────────────────────────────────
# lint_post._FENCE_RE 와 동일 — 코드펜스 인식 (CONV-01)
_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
# callout 헤더: `> [!타입]` (foldable +/- 는 §6 에서 무시). title 은 선택.
_CALLOUT_RE = re.compile(r"^>\s?\[!(\w+)\][-+]?\s*(.*?)\s*$")
# blockquote 본문 한 줄 — 선행 `> ` 하나를 벗긴다
_BQ_RE = re.compile(r"^>\s?(.*)$")
# 중첩 inner 의 callout 마커 (평문화 후 검사)
_NESTED_MARKER_RE = re.compile(r"^\[!(\w+)\][-+]?\s*(.*?)\s*$")

# 인라인 변환 (CONV-02) — 순서는 _convert_inline 에서 엄수 (CONV-03)
_MATH_RE = re.compile(r"\$[^$\n]+\$")
_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


class SpecError(Exception):
    """명세 문서를 파싱하지 못했을 때 — 파일/원인/수정법을 담는다."""


@dataclass(frozen=True)
class Finding:
    level: str
    rule_id: str
    message: str


# ── 명세 로더 (doc-parse) ──────────────────────────────────────────────────
def _find_guides_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "guides" / "callouts.md"
        if candidate.exists():
            return parent / "guides"
    raise SpecError(
        "guides/callouts.md 를 찾지 못했습니다. "
        "저장소 루트에서 실행하고 guides/ 디렉토리가 있는지 확인하세요."
    )


def _extract_section(text: str, header: str) -> str:
    """`header` 로 시작하는 줄부터 다음 동급/상위 헤더 전까지."""
    out: list[str] = []
    capturing = False
    for line in text.splitlines():
        if line.startswith(header):
            capturing = True
            continue
        if capturing and re.match(r"^#{1,3} ", line):
            break
        if capturing:
            out.append(line)
    return "\n".join(out)


def _table_cells(line: str) -> list[str]:
    """마크다운 표 한 행을 셀 목록으로. 표 행이 아니면 빈 목록."""
    if not line.lstrip().startswith("|"):
        return []
    return [c.strip() for c in line.strip().strip("|").split("|")]


@lru_cache(maxsize=None)
def load_default_titles(guides_dir: str) -> dict[str, str]:
    """callouts.md §3 표 → {타입: 기본 타이틀}. CONV-05.

    타입 셀은 백틱 코드스팬(`` `note` ``), 타이틀 셀은 평문(`노트`)이다.
    헤더·구분선 행은 백틱이 없어 자연히 걸러진다.
    """
    doc = Path(guides_dir) / "callouts.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — 기본 타이틀을 읽을 수 없습니다.")
    section = _extract_section(doc.read_text(encoding="utf-8"), "## 3")
    if not section:
        raise SpecError(
            f"{doc} 에서 '## 3' (8종 타입) 섹션을 찾지 못했습니다. "
            "헤더가 '## 3' 으로 시작하는지 확인하세요."
        )
    titles: dict[str, str] = {}
    for line in section.splitlines():
        cells = _table_cells(line)
        if len(cells) < 2:
            continue
        m = re.fullmatch(r"`(\w+)`", cells[0])
        if m and cells[1]:
            titles[m.group(1)] = cells[1]
    if not titles:
        raise SpecError(
            f"{doc} §3 표에서 기본 타이틀을 읽지 못했습니다. "
            "표 행이 `| \\`타입\\` | 기본 타이틀 | ... |` 형식인지 확인하세요."
        )
    return titles


@lru_cache(maxsize=None)
def load_aliases(guides_dir: str) -> dict[str, str]:
    """callouts.md §4 표 → {alias: 정규 클래스}. CONV-04 (27개 → 8종).

    왼쪽 셀의 모든 백틱 코드스팬이 alias, 오른쪽 셀 첫 코드스팬이 정규 클래스다.
    `note` (fallback) 같은 주석은 첫 코드스팬만 읽어 무시한다.
    """
    doc = Path(guides_dir) / "callouts.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — alias 표를 읽을 수 없습니다.")
    section = _extract_section(doc.read_text(encoding="utf-8"), "## 4")
    if not section:
        raise SpecError(
            f"{doc} 에서 '## 4' (Alias) 섹션을 찾지 못했습니다. "
            "헤더가 '## 4' 로 시작하는지 확인하세요."
        )
    aliases: dict[str, str] = {}
    for line in section.splitlines():
        cells = _table_cells(line)
        if len(cells) < 2:
            continue
        keys = re.findall(r"`(\w+)`", cells[0])
        canon = re.search(r"`(\w+)`", cells[1])
        if not keys or not canon:
            continue
        for k in keys:
            aliases[k.lower()] = canon.group(1)
    if not aliases:
        raise SpecError(
            f"{doc} §4 표에서 alias 를 읽지 못했습니다. "
            "표 행이 `| \\`alias\\` ... | \\`클래스\\` |` 형식인지 확인하세요."
        )
    return aliases


# ── 인라인 마크다운 변환 (CONV-02 / CONV-03) ───────────────────────────────
def _convert_inline(text: str) -> str:
    """callout 본문 한 줄의 인라인 마크다운을 HTML 로.

    순서 엄수 (CONV-03): $...$ 마스킹 → 코드 마스킹 → HTML 이스케이프 →
    **굵게** → *기울임* → [링크] → 코드 복원 → $...$ 복원.
    수식·코드를 먼저 빼두어야 그 안의 `*`/`[` 가 태그로 오인되지 않는다.
    """
    store: dict[str, str] = {}
    code_tokens: set[str] = set()
    counter = 0

    def _token() -> str:
        nonlocal counter
        tok = f"\x00{counter}\x00"
        counter += 1
        return tok

    # 1. $...$ 는 그대로 통과 (KaTeX). 원문 그대로 보관.
    def _mask_math(m: re.Match[str]) -> str:
        tok = _token()
        store[tok] = m.group(0)
        return tok

    text = _MATH_RE.sub(_mask_math, text)

    # 2. 인라인 코드 → 나중에 <code> 로 복원. 내용은 여기서 이스케이프.
    def _mask_code(m: re.Match[str]) -> str:
        tok = _token()
        store[tok] = html.escape(m.group(1), quote=False)
        code_tokens.add(tok)
        return tok

    text = _CODE_RE.sub(_mask_code, text)

    # 3. HTML 이스케이프 (<, >, &). placeholder 의 \x00 은 영향받지 않는다.
    text = html.escape(text, quote=False)

    # 4~6. 강조·링크
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    text = _LINK_RE.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)

    # 7~8. 복원 (코드는 <code> 로, 수식은 원문 그대로)
    for tok, value in store.items():
        replacement = f"<code>{value}</code>" if tok in code_tokens else value
        text = text.replace(tok, replacement)
    return text


# ── callout 렌더링 ─────────────────────────────────────────────────────────
def _flatten_nested(raw: str) -> tuple[str, bool]:
    """중첩 inner 본문 줄을 평문화한다 (CONV-06).

    선행 `>` 를 모두 벗기고, 남은 텍스트가 `[!타입]` 마커면 마커를 떼어낸다.
    반환: (평문 내용, 중첩이었는지).
    """
    content = raw
    nested = False
    while content.startswith(">"):
        content = content[1:]
        if content.startswith(" "):
            content = content[1:]
        nested = True
    if nested:
        m = _NESTED_MARKER_RE.match(content)
        if m:
            content = m.group(2)
    return content, nested


def _render_callout(
    alias: str,
    title_text: str,
    body_lines: list[str],
    aliases: dict[str, str],
    titles: dict[str, str],
) -> tuple[str, list[Finding]]:
    """callout 블록 하나를 <blockquote> HTML 로. (html, warnings)."""
    warnings: list[Finding] = []
    canonical = aliases.get(alias.lower())
    if canonical is None:
        canonical = "note"
        warnings.append(
            Finding(
                WARN,
                "CONV-04",
                f"알 수 없는 callout 타입 '{alias}' → note 로 처리한다. "
                "callouts.md §4 alias 표를 확인하라.",
            )
        )

    paras: list[str] = []
    nested_warned = False
    for raw in body_lines:
        content, nested = _flatten_nested(raw)
        if nested and not nested_warned:
            warnings.append(
                Finding(
                    WARN,
                    "CONV-06",
                    "중첩 callout 은 미지원 — inner 를 평문화하고 [!] 마커를 제거한다. "
                    "callouts.md §6 참조.",
                )
            )
            nested_warned = True
        if content.strip() == "":
            continue
        paras.append(f"  <p>{_convert_inline(content)}</p>")

    title = title_text.strip() or titles[canonical]
    out = [f'<blockquote class="markdown-callout markdown-callout-{canonical}">']
    out.append(f'  <p class="callout-title">{_convert_inline(title)}</p>')
    out.extend(paras)
    out.append("</blockquote>")
    return "\n".join(out), warnings


# ── 오케스트레이션 ─────────────────────────────────────────────────────────
def _fence_mask(lines: list[str]) -> list[bool]:
    """각 줄이 코드펜스 안(또는 펜스 구분선 자체)이면 True (CONV-01)."""
    mask = [False] * len(lines)
    fence_char: str | None = None
    for i, line in enumerate(lines):
        m = _FENCE_RE.match(line)
        if fence_char is None:
            if m:
                fence_char = m.group(2)[0]
                mask[i] = True  # 여는 펜스
        else:
            mask[i] = True  # 펜스 내부 + 닫는 펜스
            if m and m.group(2)[0] == fence_char and m.group(3).strip() == "":
                fence_char = None
    return mask


def convert_text(
    text: str, aliases: dict[str, str], titles: dict[str, str]
) -> tuple[str, list[Finding]]:
    """마크다운 전체를 변환한다. callout 만 HTML 로, 나머지는 그대로.

    반환: (변환된 텍스트, 경고 목록).
    """
    lines = text.splitlines()
    fence = _fence_mask(lines)
    out: list[str] = []
    warnings: list[Finding] = []

    i = 0
    n = len(lines)
    while i < n:
        # 코드펜스 안(CONV-01)이거나 callout 헤더가 아니면 그대로 통과
        if fence[i]:
            out.append(lines[i])
            i += 1
            continue
        m = _CALLOUT_RE.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue

        # callout 블록 수집: 이어지는 `>` 줄. 새 callout 헤더/펜스/비인용 줄에서 종료.
        alias, title_text = m.group(1), m.group(2)
        body: list[str] = []
        j = i + 1
        while j < n and not fence[j]:
            if _CALLOUT_RE.match(lines[j]):
                break  # 새 callout 시작 → 병합 방지
            bm = _BQ_RE.match(lines[j])
            if bm is None:
                break  # blockquote 가 아닌 줄 → 블록 종료
            body.append(bm.group(1))
            j += 1

        block, block_warnings = _render_callout(alias, title_text, body, aliases, titles)
        out.append(block)
        warnings.extend(block_warnings)
        i = j

    result = "\n".join(out)
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result, warnings


def convert(text: str, guides_dir: str | None = None) -> tuple[str, list[Finding]]:
    """명세를 로드해 변환한다 (편의 함수)."""
    gd = guides_dir or str(_find_guides_dir())
    return convert_text(text, load_aliases(gd), load_default_titles(gd))


def _print_warnings(warnings: list[Finding]) -> None:
    for w in warnings:
        print(f"  [{w.level}] {w.rule_id}: {w.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="convert-callouts",
        description="Obsidian callout → Tistory HTML 변환 (guides/RULES.md CONV-01~06)",
    )
    parser.add_argument("input", help="입력 마크다운 파일")
    parser.add_argument("-o", "--output", help="출력 파일 (기본: stdout)")
    parser.add_argument(
        "--check", action="store_true", help="변환하지 않고 진단만. 경고가 있으면 exit 1"
    )
    args = parser.parse_args(argv)

    path = Path(args.input)
    if not path.exists():
        print(f"[SpecError] 입력 파일이 없습니다: {path}", file=sys.stderr)
        return 2

    try:
        guides = str(_find_guides_dir())
        aliases = load_aliases(guides)
        titles = load_default_titles(guides)
        rendered, warnings = convert_text(path.read_text(encoding="utf-8"), aliases, titles)
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2

    if args.check:
        _print_warnings(warnings)
        if warnings:
            return 1
        print("OK — 경고 없음.", file=sys.stderr)
        return 0

    _print_warnings(warnings)
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
