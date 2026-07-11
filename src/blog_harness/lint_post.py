"""발행글 마크다운 린터 — guides/RULES.md 의 POST-01~11 을 강제한다.

파이프라인의 게이트다. 카테고리·태그·구조를 `make check` 에서 기계로 검증해, 매번
손으로 확인하던 것을 규칙 ID를 출력하는 자동 검사로 바꾼다. RULES.md 가 계약서다 —
규칙을 지어내지 않는다.

설계 경계 ([[parse-vs-constant-boundary]]):
  - **자라는 목록은 문서에서 파싱한다** — 카테고리(categories.md CATEGORIES 블록),
    Source 태그(tags.md §4 표). 명세는 한 곳에만 존재해야 한다. 코드에 상수로 박으면
    두 곳이 어긋난다 (실제로 OSS Tools 누락 사고가 있었다).
  - **유한·안정 목록은 코드 상수로 둔다** — Kind enum, 금지 목록(주관적·개인분류),
    개수 상한. 각 상수에 규칙 ID 주석을 달아 RULES.md 와 동기화한다.
  - 파싱 실패는 SpecError 로 — 어느 파일의 무엇이 잘못됐고 어떻게 고치는지 담는다.

최우선 제약: **false positive 금지.** 멀쩡한 글을 잡으면 사람이 린터를 무시하고, 그
순간 하네스는 죽는다. 애매하면 ERROR가 아니라 WARN. POST-05a(복수형)가 그래서 WARN이다.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# ── 수준 매핑 ──────────────────────────────────────────────────────────────
# guides/RULES.md § "수준" 및 각 규칙 헤더의 (ERROR/WARN/INFO) 와 동기화할 것
ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

# ── 개수·enum 상수 (RULES.md 와 동기화할 것) ───────────────────────────────
# guides/RULES.md § POST-02 — 태그 개수 상한 / tags.md §2
TOPIC_MIN, TOPIC_MAX = 1, 6
SOURCE_MAX = 1
KIND_MAX = 1
TOTAL_MIN, TOTAL_MAX = 1, 8

# guides/RULES.md § POST-03 — Kind enum + deprecated / tags.md §5
KIND_TAGS = frozenset({"회고", "정리", "트러블슈팅", "입문"})
DEPRECATED_KIND = frozenset({"삽질"})

# guides/RULES.md § POST-05b — 주관적 태그 (유한 목록, 오탐 없음) / tags.md §6
SUBJECTIVE_TAGS = frozenset({"추천", "꿀팁", "핵심", "필수", "완벽", "총정리"})

# guides/RULES.md § POST-05c — 개인 분류 태그 (유한 목록 + '/' 경로 형식) / tags.md §6
PERSONAL_TAGS = frozenset({"기억할것", "공부", "나중에"})

# guides/RULES.md § POST-05a — 복수형 허용 목록. **자라는 목록**이다 (promote 대상):
#   WARN 을 confirm 하면 여기 등록되고 다음부터 조용해진다 (팔레트 승격 SVG-08 과 동형).
NOT_PLURAL = frozenset({
    "Redis", "Kubernetes", "HTTPS", "macOS", "DNS", "Windows", "AWS", "iOS",
    "Emacs", "Analytics", "News", "SaaS", "TLS", "DDoS", "CORS", "CSS",
})
# guides/RULES.md § POST-05a — 's' 로 끝나지만 복수형이 아닌 접미사 (Class·Bus·Axis·macOS)
PLURAL_SAFE_SUFFIX = ("ss", "us", "is", "os")

# ── 정규식 ─────────────────────────────────────────────────────────────────
_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_HEADING_RE = re.compile(r"^(#{1,6})\s")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
# guides/RULES.md § POST-10 — 본문 산문의 대시. em(—)·en(–) 둘 다. 가운뎃점(·)·하이픈(-)은 제외
_BODY_DASHES = ("—", "–")


class SpecError(Exception):
    """명세 문서를 파싱하지 못했을 때 — 파일/원인/수정법을 담는다."""


@dataclass(frozen=True)
class Finding:
    level: str
    rule_id: str
    message: str


# ── 문서 로케이터 ──────────────────────────────────────────────────────────
def _find_guides_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "guides" / "categories.md"
        if candidate.exists():
            return parent / "guides"
    raise SpecError(
        "guides/categories.md 를 찾지 못했습니다. "
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
def load_categories(guides_dir: str) -> frozenset[str]:
    """categories.md 의 CATEGORIES:BEGIN/END 블록을 줄 단위로 파싱한다.

    `OSS Tools` 처럼 공백을 포함하므로 토큰 분할이 아니라 **줄 단위**로 읽는다.
    """
    doc = Path(guides_dir) / "categories.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — 유효 카테고리를 읽을 수 없습니다.")
    text = doc.read_text(encoding="utf-8")
    m = re.search(
        r"<!--\s*CATEGORIES:BEGIN\s*-->(.*?)<!--\s*CATEGORIES:END\s*-->", text, re.DOTALL
    )
    if not m:
        raise SpecError(
            f"{doc} 에서 CATEGORIES:BEGIN/END 블록을 찾지 못했습니다. "
            "'<!-- CATEGORIES:BEGIN -->' / '<!-- CATEGORIES:END -->' 마커가 있는지 확인하세요."
        )
    cats = frozenset(ln.strip() for ln in m.group(1).splitlines() if ln.strip())
    if not cats:
        raise SpecError(
            f"{doc} CATEGORIES 블록이 비어 있습니다. 카테고리를 한 줄에 하나씩 넣으세요."
        )
    return cats


@lru_cache(maxsize=None)
def load_source_tags(guides_dir: str) -> frozenset[str]:
    """tags.md §4 표의 각 행 첫 백틱 코드스팬을 Source 태그로 파싱한다.

    POST-02 축 분류에 쓴다 (Topic = 전체 − Kind − Source). 미등재 Source 는 Topic 으로
    세지므로 오탐 위험이 낮다 (Source 0 은 유효, Topic 상한 6 에 여유).
    """
    doc = Path(guides_dir) / "tags.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — Source 태그 목록을 읽을 수 없습니다.")
    section = _extract_section(doc.read_text(encoding="utf-8"), "## 4")
    if not section:
        raise SpecError(
            f"{doc} 에서 '## 4' (축 2 — Source) 섹션을 찾지 못했습니다. "
            "헤더가 '## 4' 로 시작하는지 확인하세요."
        )
    sources: set[str] = set()
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        m = re.search(r"`([^`]+)`", line)
        if m:
            sources.add(m.group(1).strip())
    if not sources:
        raise SpecError(
            f"{doc} §4 표에서 Source 태그를 읽지 못했습니다. "
            "표 행이 `| \\`태그\\` | 출처 |` 형식인지 확인하세요."
        )
    return frozenset(sources)


# ── 코드펜스 인식 ──────────────────────────────────────────────────────────
def _fence_mask(lines: list[str]) -> list[bool]:
    """각 줄이 코드펜스 안(또는 펜스 구분선 자체)이면 True. 본문 체크에서 스킵용."""
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


# ── 메타데이터 체크 (--category / --tags) ──────────────────────────────────
def check_category(category: str, valid_categories: frozenset[str]) -> list[Finding]:
    """POST-01 — 카테고리가 CATEGORIES 블록에 있어야 한다."""
    if category not in valid_categories:
        return [
            Finding(
                ERROR,
                "POST-01",
                f"카테고리 '{category}' 는 유효 목록에 없다. "
                "categories.md 의 CATEGORIES 블록을 확인하라.",
            )
        ]
    return []


def _looks_plural(tag: str) -> bool:
    """POST-05a — 휴리스틱 복수형 판정. 오탐 억제를 위해 허용 목록·접미사로 걸러낸다."""
    if tag in NOT_PLURAL:
        return False
    low = tag.lower()
    if not low.endswith("s"):
        return False
    if low.endswith(PLURAL_SAFE_SUFFIX):
        return False
    return True


def check_tags(
    tags: list[str], valid_categories: frozenset[str], source_tags: frozenset[str]
) -> list[Finding]:
    """POST-02~05 — 태그 개수·Kind·동명·금지 태그를 검사한다."""
    findings: list[Finding] = []
    n = len(tags)
    kinds = [t for t in tags if t in KIND_TAGS]
    deprecated = [t for t in tags if t in DEPRECATED_KIND]
    sources = [t for t in tags if t in source_tags]
    topics = [
        t
        for t in tags
        if t not in KIND_TAGS and t not in DEPRECATED_KIND and t not in source_tags
    ]

    # POST-02 — 개수
    if not (TOTAL_MIN <= n <= TOTAL_MAX):
        findings.append(
            Finding(ERROR, "POST-02", f"태그 총 {n}개 — {TOTAL_MIN}~{TOTAL_MAX}개여야 한다.")
        )
    if len(sources) > SOURCE_MAX:
        findings.append(
            Finding(
                ERROR, "POST-02", f"Source 태그가 {len(sources)}개 {sources} — 최대 {SOURCE_MAX}개."
            )
        )
    if not (TOPIC_MIN <= len(topics) <= TOPIC_MAX):
        findings.append(
            Finding(
                ERROR,
                "POST-02",
                f"Topic 태그가 {len(topics)}개 {topics} — {TOPIC_MIN}~{TOPIC_MAX}개여야 한다.",
            )
        )

    # POST-03 — Kind
    if deprecated:
        findings.append(
            Finding(ERROR, "POST-03", f"deprecated 태그 {deprecated} — '트러블슈팅' 으로 통일한다.")
        )
    if len(kinds) > KIND_MAX:
        findings.append(
            Finding(ERROR, "POST-03", f"Kind 태그가 {len(kinds)}개 {kinds} — 최대 {KIND_MAX}개.")
        )

    # POST-04 — 카테고리 동명
    for t in tags:
        if t in valid_categories:
            findings.append(
                Finding(
                    ERROR,
                    "POST-04",
                    f"태그 '{t}' 가 카테고리와 동명. 카테고리는 도메인, 태그는 횡단 조회 — 역할이 겹친다.",
                )
            )

    # POST-05b — 주관적
    for t in tags:
        if t in SUBJECTIVE_TAGS:
            findings.append(
                Finding(ERROR, "POST-05b", f"주관적 태그 '{t}' — 검색어가 아니다.")
            )

    # POST-05c — 개인 분류 (유한 목록 + 경로 형식)
    for t in tags:
        if t in PERSONAL_TAGS or "/" in t:
            findings.append(
                Finding(
                    ERROR, "POST-05c", f"개인 분류 태그 '{t}' — Obsidian용이지 블로그용이 아니다."
                )
            )

    # POST-05a — 복수형 (WARN, 등록 경로 안내)
    for t in tags:
        if _looks_plural(t):
            findings.append(
                Finding(
                    WARN,
                    "POST-05a",
                    f"'{t}' 가 복수형으로 보인다. '{t[:-1]}' 를 의도했나? "
                    "고유명이면 NOT_PLURAL 에 등록하라.",
                )
            )

    return findings


# ── 본문 체크 (파일당) ─────────────────────────────────────────────────────
def check_image_refs(text: str, repo_root: Path | str | None = None) -> list[Finding]:
    """POST-07 — ![alt](name.png) 의 name.png 가 diagrams/ 아래 존재, alt 비면 WARN.

    `[IMG: ...]` placeholder 는 `!` 가 없어 매치되지 않는다 (초안 형식 그대로 통과).
    http(s) URL 은 원격 이미지이므로 존재 검사에서 제외한다 (링크 생존은 POST-06/lychee).
    """
    root = Path(repo_root) if repo_root is not None else _find_repo_root()
    diagrams = root / "diagrams"
    lines = text.splitlines()
    mask = _fence_mask(lines)
    findings: list[Finding] = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        for m in _IMG_RE.finditer(line):
            alt, target = m.group(1), m.group(2).strip()
            parts = target.split()
            url = parts[0] if parts else ""
            name = Path(url).name
            if not alt.strip():
                findings.append(
                    Finding(WARN, "POST-07", f"이미지 alt 텍스트가 비어 있다 (line {i + 1}): {name}")
                )
            if url.startswith(("http://", "https://")):
                continue  # 원격 이미지 — 존재 검사 제외
            if name and not (diagrams.exists() and list(diagrams.rglob(name))):
                findings.append(
                    Finding(
                        ERROR,
                        "POST-07",
                        f"이미지 '{name}' 를 diagrams/ 아래에서 찾을 수 없다 (line {i + 1}).",
                    )
                )
    return findings


def check_section_depth(text: str) -> list[Finding]:
    """POST-08 — #### 이하 금지, # 은 제목에만 (WARN)."""
    lines = text.splitlines()
    mask = _fence_mask(lines)
    findings: list[Finding] = []
    seen_h1 = False
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = _HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        if level >= 4:
            findings.append(
                Finding(WARN, "POST-08", f"#### 이하 섹션 (line {i + 1}) — ##/### 까지만 쓴다.")
            )
        elif level == 1:
            if seen_h1:
                findings.append(
                    Finding(WARN, "POST-08", f"# 은 제목에만 (line {i + 1}) — 섹션은 ## 부터.")
                )
            seen_h1 = True
    return findings


def check_conclusion(text: str) -> list[Finding]:
    """POST-09 — 마지막 ## 섹션이 '마무리' 또는 '정리' 여야 한다 (WARN)."""
    lines = text.splitlines()
    mask = _fence_mask(lines)
    last_h2: str | None = None
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = _H2_RE.match(line)
        if m:
            last_h2 = m.group(1).strip()
    if last_h2 is None:
        return [
            Finding(WARN, "POST-09", "## 최상위 섹션이 없다 — 글은 '## 마무리'/'## 정리' 로 끝난다.")
        ]
    if last_h2 not in ("마무리", "정리"):
        return [
            Finding(
                WARN,
                "POST-09",
                f"마지막 섹션이 '## {last_h2}' — '## 마무리' 또는 '## 정리' 로 끝낸다.",
            )
        ]
    return []


def check_body_dash(text: str) -> list[Finding]:
    """POST-10 — 본문 산문의 대시(—) 는 WARN. #·[IMG:·| 로 시작하는 줄은 검사 대상 아님.

    실측: 대시 77회 중 본문 산문 11회만 대상. 나머지 66회(제목·IMG·표)를 스킵해야 오탐이 없다.
    인라인 코드(`...`)는 제거 후 본다. 가운뎃점(·)·하이픈(-)은 잡지 않는다.
    """
    lines = text.splitlines()
    mask = _fence_mask(lines)
    findings: list[Finding] = []
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        stripped = line.lstrip()
        if stripped.startswith(("#", "[IMG:", "|")):
            continue
        cleaned = _INLINE_CODE_RE.sub("", line)
        if any(d in cleaned for d in _BODY_DASHES):
            snippet = line.strip()
            if len(snippet) > 50:
                snippet = snippet[:50] + "…"
            findings.append(
                Finding(
                    WARN,
                    "POST-10",
                    f'본문 산문에 대시(—) (line {i + 1}): "{snippet}" — 문장을 끊거나(.) 쉼표로 잇는다.',
                )
            )
    return findings


def check_code_lang(text: str) -> list[Finding]:
    """POST-11 — 여는 코드펜스에 언어 태그가 없으면 WARN."""
    findings: list[Finding] = []
    fence_char: str | None = None
    for i, line in enumerate(text.splitlines()):
        m = _FENCE_RE.match(line)
        if not m:
            continue
        char, info = m.group(2)[0], m.group(3).strip()
        if fence_char is None:
            fence_char = char
            if not info:
                findings.append(
                    Finding(
                        WARN, "POST-11", f"코드 블록에 언어 태그 없음 (line {i + 1}) — ```python 처럼 명시."
                    )
                )
        elif char == fence_char and info == "":
            fence_char = None
    return findings


# ── 죽은 링크 (POST-06) ────────────────────────────────────────────────────
def check_dead_links(
    paths: list[str], skip: bool = False
) -> tuple[list[Finding], bool]:
    """POST-06 — lychee 로 죽은 링크 검사. 반환: (findings, skipped).

    lychee 가 없으면 안내를 출력하고 스킵한다. 네트워크가 정답성의 의존이 되면 안 된다.
    """
    if skip:
        return [], True
    if shutil.which("lychee") is None:
        print(
            "[POST-06] lychee 가 설치돼 있지 않아 죽은 링크 검사를 건너뜁니다 "
            "(설치: https://github.com/lycheeverse/lychee). 나머지 검사는 계속합니다.",
            file=sys.stderr,
        )
        return [], True
    proc = subprocess.run(
        ["lychee", "--no-progress", *paths], capture_output=True, text=True
    )
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return [Finding(ERROR, "POST-06", "죽은 링크 발견 — 위 lychee 출력 참조.")], False
    return [], False


# ── 오케스트레이션 ─────────────────────────────────────────────────────────
def lint_post_text(
    text: str, path: str = "mem.md", repo_root: Path | str | None = None
) -> list[Finding]:
    """한 마크다운 텍스트에 본문 체크(POST-07~11)를 적용한다. 테스트 코어.

    메타데이터 체크(POST-01~05)는 CLI 인자에서 오므로 여기 없다 — lint_metadata 참조.
    """
    findings: list[Finding] = []
    findings += check_image_refs(text, repo_root)
    findings += check_section_depth(text)
    findings += check_conclusion(text)
    findings += check_body_dash(text)
    findings += check_code_lang(text)
    return findings


def lint_metadata(
    category: str | None, tags: list[str] | None, guides_dir: str | None = None
) -> list[Finding]:
    """POST-01~05 — 카테고리·태그 메타데이터를 검사한다 (파일 무관, 1회)."""
    gd = guides_dir if guides_dir is not None else str(_find_guides_dir())
    valid = load_categories(gd)
    sources = load_source_tags(gd)
    findings: list[Finding] = []
    if category is not None:
        findings += check_category(category, valid)
    if tags is not None:
        findings += check_tags(tags, valid, sources)
    return findings


def lint_file(path: Path) -> list[Finding]:
    return lint_post_text(path.read_text(encoding="utf-8"), str(path))


def iter_md_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out += sorted(p.rglob("*.md"))
        elif p.suffix.lower() == ".md":
            out.append(p)
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _run_lint(
    paths: list[str],
    category: str | None,
    tags: list[str] | None,
    strict: bool,
    no_links: bool,
) -> int:
    files = iter_md_files(paths)
    total_error = total_warn = 0

    def emit(header: str, fs: list[Finding]) -> None:
        nonlocal total_error, total_warn
        if not fs:
            return
        print(header)
        for f in fs:
            print(f"  [{f.level}] {f.rule_id}: {f.message}")
            if f.level == ERROR:
                total_error += 1
            elif f.level == WARN:
                total_warn += 1

    meta = lint_metadata(category, tags) if (category is not None or tags is not None) else []

    if len(files) == 1:
        # 단일 파일: 메타데이터 + 본문을 한 헤더 아래 묶어 출력 (헤더 중복 방지)
        emit(str(files[0]), meta + lint_file(files[0]))
    else:
        if meta:
            emit("메타데이터 (--category/--tags)", meta)
        for path in files:
            emit(str(path), lint_file(path))

    # 죽은 링크 (POST-06, 검사 대상 파일이 있을 때 1회)
    if files:
        link_findings, _ = check_dead_links([str(p) for p in files], skip=no_links)
        emit("죽은 링크 (POST-06)", link_findings)

    if not files and category is None and tags is None:
        print("검사할 마크다운 파일이 없습니다.", file=sys.stderr)
        return 0

    if total_error or total_warn:
        print(f"\n{len(files)}개 검사 — ERROR {total_error}, WARN {total_warn}")
    if total_error:
        return 1
    if strict and total_warn:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint-post", description="발행글 마크다운 린터 (guides/RULES.md POST-01~11)"
    )
    parser.add_argument("paths", nargs="+", help="마크다운 파일 또는 디렉토리(재귀)")
    parser.add_argument("--category", help="글의 카테고리 (POST-01)")
    parser.add_argument("--tags", help="콤마로 구분한 태그 목록 (POST-02~05)")
    parser.add_argument("--strict", action="store_true", help="WARN 도 실패로 처리")
    parser.add_argument("--no-links", action="store_true", help="죽은 링크 검사(POST-06) 스킵")
    args = parser.parse_args(argv)

    tags = None
    if args.tags is not None:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    try:
        return _run_lint(args.paths, args.category, tags, args.strict, args.no_links)
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
