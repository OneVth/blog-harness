"""크로스 프로바이더 팩트체커 — guides/RULES.md 의 FACT-01~04 를 강제한다.

AI가 쓴 글에는 출처 없는 검증 가능한 주장이 섞인다 ("Anima는 20억 파라미터"). 지금은
매번 사람이 검증한다. 축적될수록 오염 비용이 커진다. 그래서 GPT에게 팩트체크를 시킨다 —
**그런데 그냥 시키면 실패한다.** "출처 없이 지어냄"은 Claude와 GPT가 공유하는 실수라,
"이거 맞아?"라고 물으면 GPT가 자기 훈련 데이터로 "맞네" 하고 넘긴다. **프로바이더를
건너서도 에코 챔버가 발생한다.** 그래서 판정 기준을 바꾼다 (FACT-02):

    ✗ "이 주장이 사실인가?"     ← GPT의 지식에 의존. 오염됨
    ✓ "글 안에 근거가 있는가?"   ← 텍스트 구조만 본다

**진짜 산출물은 코드가 아니라 프롬프트다.** 이 모듈은 얇다 — 본문 추출 → 프롬프트 파일
생성 → GPT 응답(JSON) 파싱 → 심각도순 리포트. **API를 쓰지 않는다**: 프롬프트를 파일로
뱉으면 사람이 GPT 창에 붙여넣고 응답을 저장한다.

최우선 제약: **false positive 금지.** EXPERIENCE(1인칭 경험·환경 특정 관찰)가 그 가드다
(FACT-01). "내 RTX 4060에서는 안 먹었다"를 UNSOURCED 로 잡으면 오탐이 쏟아지고, 그 순간
사람이 팩트체커를 무시한다.

설계 경계 ([[parse-vs-constant-boundary]]):
  - **자라는 목록은 문서에서 파싱한다** — 출처 필요/불필요 표(writing.md §2.1). 명세는
    한 곳에만 존재해야 한다. 무엇에 출처가 필요한지 바뀌면 프롬프트가 자동으로 따라온다.
  - **유한·안정 목록은 코드 상수로 둔다** — MAX_ROUNDS, 판정 카테고리, 정렬 순서.
    각 상수에 규칙 ID 주석을 달아 RULES.md 와 동기화한다.
  - 파싱 실패는 SpecError 로 — 어느 파일의 무엇이 잘못됐고 어떻게 고치는지 담는다.

판정자는 조언한다. 명령하지 않는다 (FACT-04). 이 도구는 리포트만 낸다 — 자동 수정도
자동 통과도 없다. 초안은 사람이 고친다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# ── 상수 (RULES.md 와 동기화할 것) ─────────────────────────────────────────
# guides/RULES.md § FACT-03 — 라운드 하드 캡. 루프는 언제나 여기서 종료된다.
MAX_ROUNDS = 3

# guides/RULES.md § FACT-01 — 개별 출력하는 판정(심각도순). 앞이 더 심각하다.
SEVERITY_ORDER = ("CONTRADICTED", "UNSOURCED", "HEDGE_NEEDED")
# guides/RULES.md § FACT-01 — 통과 판정. 개별 출력하지 않고 요약 카운트에만 (노이즈 방지).
PASSING = ("VERIFIED", "EXPERIENCE")
# 알려진 판정 전체. 이 밖의 값은 오탈자·신규로 보고 개별 출력해 사람에게 노출한다.
KNOWN_VERDICTS = frozenset(SEVERITY_ORDER) | frozenset(PASSING)

# ── 프롬프트 조각 (RULES.md 인용 — 프롬프트가 진짜 산출물이다) ──────────────
# guides/RULES.md § FACT-02 — 반드시 프롬프트에 넣는다. 에코 챔버 차단의 핵심.
_JUDGE_INSTRUCTION = (
    '너 자신의 지식으로 "맞는 것 같다"고 판단하지 마라.\n'
    "글 안에 근거가 제시돼 있는지만 본다."
)
# guides/RULES.md § FACT-01 — 판정 카테고리.
_CATEGORIES = """\
VERIFIED      출처가 명시돼 있고 그 출처가 주장을 지지함
CONTRADICTED  출처와 본문이 어긋남
UNSOURCED     사실처럼 서술됐지만 출처가 없음
HEDGE_NEEDED  통념·경험담인데 단정형으로 쓰임
EXPERIENCE    1인칭 경험·환경 특정 관찰. 출처 불필요"""
# guides/RULES.md § FACT-01 — EXPERIENCE 가 false-positive 가드다. 예시를 반드시 넣는다.
_EXPERIENCE_EXAMPLES = """\
다음은 UNSOURCED 가 아니라 EXPERIENCE 다 (출처 불필요):
  "내 RTX 4060에서는 이 설정이 안 먹었다"
  "내 PC의 IP가 192.168.0.10인데도 인터넷이 되는 이유는..."
1인칭 경험·환경 특정 관찰을 UNSOURCED 로 잡으면 false positive 다."""

# ── 정규식 ─────────────────────────────────────────────────────────────────
_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_ROUND_RE = re.compile(r"^##\s+Round\s+\d+", re.MULTILINE)


class SpecError(Exception):
    """명세 문서·입력을 파싱하지 못했을 때 — 파일/원인/수정법을 담는다."""


@dataclass(frozen=True)
class Claim:
    """GPT 응답의 한 항목. claim 은 본문에서 그대로 인용된 문자열."""

    claim: str
    verdict: str
    reason: str
    suggestion: str


# ── 문서 로케이터 (lint_post.py 관례 복제, 센티넬만 writing.md) ─────────────
def _find_guides_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "guides" / "writing.md"
        if candidate.exists():
            return parent / "guides"
    raise SpecError(
        "guides/writing.md 를 찾지 못했습니다. "
        "저장소 루트에서 실행하고 guides/ 디렉토리가 있는지 확인하세요."
    )


def _find_repo_root() -> Path:
    return _find_guides_dir().parent


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


# ── 자라는 목록 파서 (doc-parse) ───────────────────────────────────────────
@lru_cache(maxsize=None)
def load_source_rules(guides_dir: str) -> str:
    """writing.md §2.1 의 '출처 필요/불필요' 표를 파싱해 프롬프트용 문자열로 돌려준다.

    tags.md §4 파싱(lint_post.load_source_tags)과 동형. 무엇에 출처가 필요한지 정의가
    바뀌면 프롬프트가 자동으로 따라오도록 코드에 상수로 박지 않는다.
    """
    doc = Path(guides_dir) / "writing.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — 출처 규칙(§2.1)을 읽을 수 없습니다.")
    section = _extract_section(doc.read_text(encoding="utf-8"), "### 2.1")
    rows = [ln.strip() for ln in section.splitlines() if ln.lstrip().startswith("|")]
    if not rows:
        raise SpecError(
            f"{doc} 에서 §2.1 출처 표를 찾지 못했습니다. "
            "헤더가 '### 2.1' 로 시작하고 '| 대상 | 출처 필요 |' 표가 있는지 확인하세요."
        )
    return "\n".join(rows)


# ── 코드펜스 인식 (lint_post.py 관례 복제) ─────────────────────────────────
def _fence_mask(lines: list[str]) -> list[bool]:
    """각 줄이 코드펜스 안(또는 펜스 구분선 자체)이면 True."""
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


def _strip_frontmatter(text: str) -> str:
    """맨 앞 YAML 프런트매터(--- … ---)를 제거한다. 메타데이터는 검증 대상이 아니다."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text  # 닫는 --- 가 없으면 원문 그대로 (프런트매터로 보지 않는다)


# ── 본문 추출 ──────────────────────────────────────────────────────────────
def extract_body(text: str) -> str:
    """GPT 에 보낼 깨끗한 본문. 프런트매터·코드 블록·이미지/IMG placeholder 제거.

    코드와 이미지 placeholder 는 검증 가능한 주장이 아니다. 남기면 GPT가 코드 속 값을
    주장으로 오인해 오탐을 낸다.
    """
    body = _strip_frontmatter(text)
    lines = body.splitlines()
    mask = _fence_mask(lines)
    out: list[str] = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue  # 코드 블록
        if line.lstrip().startswith("[IMG:"):
            continue  # 초안 이미지 placeholder
        cleaned = _IMG_RE.sub("", line)  # ![alt](x.png) 이미지 마크다운 제거
        out.append(cleaned)
    return "\n".join(out).strip()


# ── 프롬프트 생성 (진짜 산출물) ────────────────────────────────────────────
def build_prompt(body: str, source_rules: str) -> str:
    """FACT-01/02 를 담은 팩트체크 프롬프트를 조립한다.

    반드시 포함: FACT-02 지시문, FACT-01 5개 카테고리 + EXPERIENCE 예시, §2.1 출처 표,
    본문, 파싱 가능한 JSON 출력 스키마.
    """
    return f"""\
당신은 기술 블로그 글의 팩트체커다. 아래 글을 문장 단위로 검토한다.

## 판정 기준 (가장 중요)

{_JUDGE_INSTRUCTION}

"출처 없이 사실을 지어냄"은 여러 AI가 공유하는 실수다. 너의 훈련 데이터로 "맞는 것
같다"고 넘기면 그 실수를 그대로 반복한다. 오직 **글 안에 근거가 제시돼 있는지**만 본다.

## 판정 카테고리

{_CATEGORIES}

{_EXPERIENCE_EXAMPLES}

## 어떤 주장에 출처가 필요한가 (writing.md §2.1)

{source_rules}

## 검토할 본문

<<<
{body}
>>>

## 출력 형식

검토가 필요한 각 주장에 대해 아래 JSON 배열만 출력한다. 설명·머리말 없이 JSON 만 낸다.
claim 은 **본문에서 그대로 인용**한다 (요약·바꿔쓰기 금지 — 원문 검색에 쓴다).

[
  {{
    "claim": "<본문에서 그대로 인용>",
    "verdict": "VERIFIED|CONTRADICTED|UNSOURCED|HEDGE_NEEDED|EXPERIENCE",
    "reason": "<왜 그렇게 판정했는지>",
    "suggestion": "<출처를 달거나 / 완화하거나 / 빼거나>"
  }}
]
"""


# ── 응답 파싱 (깨진 JSON 방어) ─────────────────────────────────────────────
def parse_response(json_text: str) -> list[Claim]:
    """GPT 응답(JSON)을 Claim 목록으로 파싱한다. 깨진 JSON 은 SpecError 로 (크래시 금지).

    GPT가 ```json 펜스나 머리말을 붙이는 경우가 잦아, 첫 '[' ~ 마지막 ']' 만 떼어 시도한다.
    """
    text = json_text.strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SpecError(
            f"응답 JSON 파싱 실패 ({e.msg}, line {e.lineno} col {e.colno}). "
            "GPT 출력에서 JSON 배열만 남기고 (```json 펜스·머리말 제거) 다시 저장하세요."
        ) from e
    if not isinstance(data, list):
        raise SpecError(
            "응답이 JSON 배열이 아닙니다. 최상위가 [ ... ] 형태여야 합니다."
        )
    claims: list[Claim] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise SpecError(f"응답 {i}번 항목이 객체가 아닙니다: {item!r}")
        if "claim" not in item or "verdict" not in item:
            raise SpecError(
                f"응답 {i}번 항목에 'claim' 또는 'verdict' 키가 없습니다: {item!r}"
            )
        claims.append(
            Claim(
                claim=str(item["claim"]),
                verdict=str(item["verdict"]).strip().upper(),
                reason=str(item.get("reason", "")),
                suggestion=str(item.get("suggestion", "")),
            )
        )
    return claims


# ── 리포트 ─────────────────────────────────────────────────────────────────
def _locate_claim(claim: str, draft_lines: list[str]) -> int | None:
    """원본 초안에서 claim 문자열을 찾아 1-기반 줄 번호. 못 찾으면 None (관용 처리)."""
    needle = claim.strip()
    if not needle:
        return None
    for i, line in enumerate(draft_lines):
        if needle in line:
            return i + 1
    return None


def _severity_key(verdict: str) -> int:
    """정렬 키. 알려진 심각도는 순서대로, 미지의 판정은 맨 뒤(하지만 출력은 됨)."""
    try:
        return SEVERITY_ORDER.index(verdict)
    except ValueError:
        return len(SEVERITY_ORDER)


def build_report(
    claims: list[Claim], draft_path: str, draft_text: str
) -> tuple[str, int, dict[str, int]]:
    """심각도순 리포트 문자열, exit_code, verdict 카운트를 돌려준다.

    PASSING(VERIFIED·EXPERIENCE)은 개별 출력하지 않고 카운트에만 넣는다 — 통과한 걸 읽는
    건 노이즈다. exit_code = 통과가 아닌 항목이 하나라도 있으면 1 (make check 체이닝용).
    """
    counts: dict[str, int] = {}
    for c in claims:
        counts[c.verdict] = counts.get(c.verdict, 0) + 1

    flagged = [c for c in claims if c.verdict not in PASSING]
    flagged.sort(key=lambda c: _severity_key(c.verdict))
    draft_lines = draft_text.splitlines()

    blocks: list[str] = []
    for c in flagged:
        line = _locate_claim(c.claim, draft_lines)
        loc = f"{draft_path}:{line}" if line is not None else f"{draft_path}:?"
        block = f'{loc}\n[{c.verdict}] "{c.claim}"'
        if c.reason:
            block += f"\n  이유: {c.reason}"
        if c.suggestion:
            block += f"\n  제안: {c.suggestion}"
        blocks.append(block)

    severity_summary = ", ".join(f"{v} {counts.get(v, 0)}" for v in SEVERITY_ORDER)
    passing_summary = ", ".join(f"{v} {counts.get(v, 0)}" for v in PASSING)
    unknown = sorted(v for v in counts if v not in KNOWN_VERDICTS)
    summary = f"{len(claims)}개 검사 — {severity_summary} · 통과 {passing_summary}"
    if unknown:
        summary += " · 미지 " + ", ".join(f"{v} {counts[v]}" for v in unknown)

    body = "\n\n".join(blocks) if blocks else "플래그된 주장 없음."
    report = f"{body}\n\n{summary}"
    exit_code = 1 if flagged else 0
    return report, exit_code, counts


# ── 라운드 로그 / 교착 (FACT-03) ───────────────────────────────────────────
def count_rounds(log_text: str) -> int:
    """로그의 '## Round N' 헤더 수. 순수 함수 — 교착 판정의 근거."""
    return len(_ROUND_RE.findall(log_text))


def _round_entry(round_no: int, claims: list[Claim], counts: dict[str, int]) -> str:
    """로그에 append 할 한 라운드 블록. 시각은 여기(IO 경계)에서만 찍는다."""
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    severity_summary = ", ".join(f"{v} {counts.get(v, 0)}" for v in SEVERITY_ORDER)
    passing_summary = ", ".join(f"{v} {counts.get(v, 0)}" for v in PASSING)
    lines = [f"## Round {round_no} — {stamp}", "", f"{severity_summary} · 통과 {passing_summary}", ""]
    flagged = [c for c in claims if c.verdict not in PASSING]
    flagged.sort(key=lambda c: _severity_key(c.verdict))
    for c in flagged:
        lines.append(f'- [{c.verdict}] "{c.claim}"')
    if not flagged:
        lines.append("- (플래그 없음 — 수렴)")
    return "\n".join(lines) + "\n"


# ── CLI: 생성 ──────────────────────────────────────────────────────────────
def _slug(draft: str) -> str:
    return Path(draft).stem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="factcheck",
        description="팩트체크 프롬프트 생성 (guides/RULES.md FACT-01~04)",
    )
    parser.add_argument("draft", help="초안 마크다운 파일 (예: drafts/foo.md)")
    args = parser.parse_args(argv)

    try:
        draft_path = Path(args.draft)
        if not draft_path.exists():
            print(f"[factcheck] 초안이 없습니다: {draft_path}", file=sys.stderr)
            return 2
        body = extract_body(draft_path.read_text(encoding="utf-8"))
        source_rules = load_source_rules(str(_find_guides_dir()))
        prompt = build_prompt(body, source_rules)

        out_dir = _find_repo_root() / "factcheck"
        out_dir.mkdir(exist_ok=True)
        slug = _slug(args.draft)
        prompt_path = out_dir / f"{slug}.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2

    print(f"프롬프트를 썼습니다: {prompt_path}")
    print(
        f"GPT에 붙여넣고 응답(JSON)을 factcheck/{slug}.response.json 에 저장한 뒤 "
        f"`make factcheck-apply POST={args.draft}` 를 실행하세요."
    )
    return 0


# ── CLI: 적용 ──────────────────────────────────────────────────────────────
def apply_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="factcheck-apply",
        description="GPT 응답을 파싱해 심각도순 리포트 출력 (자동 수정 없음)",
    )
    parser.add_argument("draft", help="초안 마크다운 파일 (예: drafts/foo.md)")
    args = parser.parse_args(argv)

    try:
        slug = _slug(args.draft)
        fc_dir = _find_repo_root() / "factcheck"
        response_path = fc_dir / f"{slug}.response.json"
        draft_path = Path(args.draft)
        if not response_path.exists():
            print(
                f"[factcheck-apply] 응답이 없습니다: {response_path}\n"
                f"먼저 `make factcheck POST={args.draft}` 로 프롬프트를 만들고 "
                "GPT 응답을 위 경로에 저장하세요.",
                file=sys.stderr,
            )
            return 2
        if not draft_path.exists():
            print(f"[factcheck-apply] 초안이 없습니다: {draft_path}", file=sys.stderr)
            return 2

        claims = parse_response(response_path.read_text(encoding="utf-8"))
        draft_text = draft_path.read_text(encoding="utf-8")
        report, exit_code, counts = build_report(claims, str(draft_path), draft_text)

        log_path = fc_dir / f"{slug}.log.md"
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        current_round = count_rounds(existing) + 1
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2

    # FACT-03 — 하드 캡. 교착은 정당한 결과다. 수렴한 척하지 않는다.
    if current_round > MAX_ROUNDS:
        print(report)
        print(
            f"\n[FACT-03] MAX_ROUNDS({MAX_ROUNDS}) 도달 — 교착. 새 라운드를 돌리지 않습니다.\n"
            f"위 미해결 주장을 사람이 판정하세요. 근거: {log_path}"
        )
        return 1

    # 라운드 append (수렴/미수렴 모두 기록 — 교착 근거)
    entry = _round_entry(current_round, claims, counts)
    with log_path.open("a", encoding="utf-8") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write(entry + "\n")

    print(report)
    print(f"\nRound {current_round}/{MAX_ROUNDS} 기록: {log_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
