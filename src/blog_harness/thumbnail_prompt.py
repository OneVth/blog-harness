"""썸네일 프롬프트 생성기 — guides/thumbnails.md 규칙을 프롬프트에 박는다.

가이드가 있어도 GPT는 매번 다르게 해석한다. 강제력이 없기 때문이다. 그래서
`factcheck` 와 같은 패턴을 쓴다 — **진짜 산출물은 코드가 아니라 프롬프트다.** 이 모듈은
스타일·캔버스·배경색·오브젝트 개수·텍스트 규칙·금지 스타일을 **결정론적으로** 프롬프트에
박아 `thumbnails/<slug>.prompt.txt` 로 뱉는다. 사람은 복붙만 한다. API 를 쓰지 않는다.

**오브젝트 자리는 비워둔다** (`{{OBJECT}}`). 오브젝트 선정은 룩업이 아니라 판단이라,
GPT 에게 맡기면 판단자 겸 생성자가 되어 "매번 다르게 해석한다" 가 재발한다
(thumbnails.md §2.4, §10). `make thumbnail-prompt` 를 실행하는 시점에 Claude 가 이미
초안을 읽고 있으니, 그 자리를 Claude 가 채운다 — 초안을 읽고 개념 하나를 오브젝트
하나로 압축한 뒤, 파일 맨 위 근거 헤더(`# 개념 / # 오브젝트 / # 근거`)에 판단을 남긴다.
`--object/--concept/--rationale` 를 주면 하네스가 대신 박는다 (두 방식 모두 지원).
GPT 는 그리기만 하고, 다른 세션의 Claude 가 150px 이미지로 블라인드 검증한다 (§8.1).

설계 경계 ([[parse-vs-constant-boundary]]):
  - **자라는 목록만 문서 파싱** — 카테고리→배경색 표(thumbnails.md §5.1
    THUMBNAIL_COLORS 블록). 카테고리가 늘면 프롬프트가 자동으로 따라온다.
  - **§2.4 개념→오브젝트 표는 파싱하지 않는다.** 그건 GPT용이 아니라 Claude 가
    오브젝트를 고를 때 보는 참조 자료다 (대부분의 글은 표에 없다 — §2.1).
  - **안정 목록은 프롬프트 조각 상수로 박되** 각 조각에 thumbnails.md §N 주석을 단다
    (factcheck._CATEGORIES 관례).
  - 파싱 실패는 SpecError 로 — 어느 파일의 무엇이 잘못됐고 어떻게 고치는지 담는다.
"""

from __future__ import annotations

import argparse
import re
import sys
from functools import lru_cache
from pathlib import Path

# ── 프롬프트 조각 (thumbnails.md 인용 — 프롬프트가 진짜 산출물이다) ──────────
# guides/thumbnails.md §4 — 기본 스타일. 협상 대상이 아니다.
_STYLE = (
    "스타일: Pixel Art / 16bit 게임 일러스트 / 레트로 개발도구 / 기술 다이어그램 /\n"
    "교육용 아이콘 계열. 차분하고 정돈된, 논리적이고 깔끔한 느낌."
)
# guides/thumbnails.md §3 — 캔버스 (guides/RULES.md § THUMB-01, THUMB-02 와 대칭).
_CANVAS = (
    "캔버스: 정사각형 1:1, 1024×1024. 16:9·4:3·3:2·세로형·와이드 배너 금지."
)
# guides/thumbnails.md §2.2 — 코드를 그리지 않는다.
_NO_CODE = (
    "코드를 그리지 않는다: 코드 스크린샷·터미널 화면·소스 문자열·브랜드 로고 금지.\n"
    "개념을 상징하는 물리적 오브젝트로 표현한다."
)
# guides/thumbnails.md §6 (guides/RULES.md § THUMB-03 무지개 금지·주색상 1개).
_OBJECT_RULES = (
    "주 오브젝트 1개(필요하면 2~3개, 3개 초과 금지). 화면의 50~70%를 차지하고 중앙\n"
    "배치, 여백 충분히. 주색상 1개 — 무지개 금지. 오브젝트가 배경보다 먼저 보여야 한다."
)
# guides/thumbnails.md §7 — 텍스트 화이트리스트. 문장 금지.
_TEXT_RULES = (
    "텍스트는 최소한. 식별자·값·분기 라벨만 허용(예: main(), 0x1000, YES, NO, malloc).\n"
    "문장·블로그 제목 전체 금지. 텍스트가 오브젝트보다 먼저 보이면 실패다."
)
# guides/thumbnails.md §4 금지 스타일.
_FORBIDDEN = (
    "금지 스타일: 사이버펑크 · 네온사인 · 과도한 광원 · 과한 입자 효과 ·\n"
    "MMORPG 아이템 아이콘 · 모바일 게임 UI · SF HUD · 복잡한 인터페이스 · 과도한 텍스트."
)

# 채워지지 않은 자리 표시자. Claude 가 초안을 읽고 채운다 (thumbnails.md §2.4).
_OBJECT_PLACEHOLDER = "{{OBJECT}}"
_CONCEPT_PLACEHOLDER = "{{CONCEPT}}"
_RATIONALE_PLACEHOLDER = "{{RATIONALE}}"

# ── 정규식 ─────────────────────────────────────────────────────────────────
# §5.1 표의 HEX 코드스팬. 행 첫 셀은 카테고리명, 둘째 셀은 `#RRGGBB`.
_HEX_RE = re.compile(r"`(#[0-9A-Fa-f]{3,8})`")


class SpecError(Exception):
    """명세 문서·입력을 파싱하지 못했을 때 — 파일/원인/수정법을 담는다."""


# ── 문서 로케이터 (factcheck.py 관례 복제, 센티넬만 thumbnails.md) ───────────
def _find_guides_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "guides" / "thumbnails.md"
        if candidate.exists():
            return parent / "guides"
    raise SpecError(
        "guides/thumbnails.md 를 찾지 못했습니다. "
        "저장소 루트에서 실행하고 guides/ 디렉토리가 있는지 확인하세요."
    )


def _find_repo_root() -> Path:
    return _find_guides_dir().parent


# ── 자라는 목록 파서 (doc-parse) ───────────────────────────────────────────
@lru_cache(maxsize=None)
def load_category_colors(guides_dir: str) -> dict[str, str]:
    """thumbnails.md §5.1 THUMBNAIL_COLORS 블록을 파싱해 {카테고리: HEX} 로 돌려준다.

    lint_post.load_categories 의 BEGIN/END 블록 파싱과 동형. 카테고리가 늘어도(표에 한
    줄 추가) 프롬프트가 자동으로 따라오도록 코드에 색을 박지 않는다. 헤더·구분선 행은
    HEX 코드스팬이 없어 자연히 걸러진다. `OSS Tools` 처럼 공백을 포함하므로 셀 단위로
    읽는다.
    """
    doc = Path(guides_dir) / "thumbnails.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — 카테고리 배경색을 읽을 수 없습니다.")
    text = doc.read_text(encoding="utf-8")
    m = re.search(
        r"<!--\s*THUMBNAIL_COLORS:BEGIN\s*-->(.*?)<!--\s*THUMBNAIL_COLORS:END\s*-->",
        text,
        re.DOTALL,
    )
    if not m:
        raise SpecError(
            f"{doc} 에서 THUMBNAIL_COLORS:BEGIN/END 블록을 찾지 못했습니다. "
            "'<!-- THUMBNAIL_COLORS:BEGIN -->' / '<!-- THUMBNAIL_COLORS:END -->' "
            "마커가 §5.1 에 있는지 확인하세요."
        )
    colors: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        hexm = _HEX_RE.search(cells[1])
        if not cells[0] or not hexm:
            continue  # 헤더(| 카테고리 | HEX | 톤 |) / 구분선(|---|---|---|)
        colors[cells[0]] = hexm.group(1)
    if not colors:
        raise SpecError(
            f"{doc} THUMBNAIL_COLORS 블록에서 카테고리 색을 읽지 못했습니다. "
            "표 행이 `| 카테고리 | \\`#RRGGBB\\` | 톤 |` 형식인지 확인하세요."
        )
    return colors


# ── 프롬프트 조립 (진짜 산출물) ────────────────────────────────────────────
def build_prompt(
    bg_hex: str,
    category: str,
    object_text: str | None = None,
    concept: str | None = None,
    rationale: str | None = None,
) -> str:
    """썸네일 생성 프롬프트를 조립한다. 오브젝트만 자리를 비우고 나머지는 결정론적이다.

    object_text 가 있으면 하네스가 박고, 없으면 {{OBJECT}} placeholder 를 남긴다 —
    Claude 가 초안을 읽고 채운다 (thumbnails.md §2.4). 맨 위 근거 헤더는 블라인드 테스트
    실패 시 오브젝트를 다시 고르는 근거가 된다 (§8.1).
    """
    obj = object_text if object_text else _OBJECT_PLACEHOLDER
    con = concept if concept else _CONCEPT_PLACEHOLDER
    rat = rationale if rationale else _RATIONALE_PLACEHOLDER
    return f"""\
# 개념: {con}
# 오브젝트: {obj}
# 근거: {rat}
#
# 위 오브젝트는 Claude 가 초안을 읽고 고른다 (thumbnails.md §2.4). GPT 는 그리기만.
# 블라인드 테스트(§8.1)가 실패하면 프롬프트가 아니라 이 판단을 다시 한다.
# ── 아래부터 GPT 이미지 생성기에 붙여넣는다 ───────────────────────────────

기술 블로그 썸네일 한 장을 만든다. 화려한 유튜브 썸네일도, 광고 배너도 아니다 —
기술 개념 하나를 직관적인 오브젝트 하나로 압축한 **교육용 아이콘**이다.

## 오브젝트 (핵심)
오브젝트: {obj}
딱 이 오브젝트 1개만 그린다.
{_OBJECT_RULES}

## 코드를 그리지 않는다
{_NO_CODE}

## 스타일
{_STYLE}

## 캔버스
{_CANVAS}

## 배경
밝은 단색 {bg_hex} (카테고리 {category}). 종이 질감 허용, 장식 최소화.
배경은 주인공이 아니다 — 배경 때문에 오브젝트가 묻히면 실패다.

## 텍스트
{_TEXT_RULES}

## 금지
{_FORBIDDEN}

## 최종 조건
150px 로 줄여도 무엇인지 보여야 한다. 디테일이 필요하면 오브젝트를 잘못 고른 것이다.
"""


# ── CLI ────────────────────────────────────────────────────────────────────
def _slug(draft: str) -> str:
    return Path(draft).stem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="thumbnail-prompt",
        description="썸네일 프롬프트 뼈대 생성 (guides/thumbnails.md)",
    )
    parser.add_argument("draft", help="초안 마크다운 파일 (예: drafts/foo.md)")
    parser.add_argument("--category", required=True, help="발행 카테고리 (예: Infra)")
    parser.add_argument("--object", dest="object_text", help="오브젝트 (생략 시 {{OBJECT}})")
    parser.add_argument("--concept", help="핵심 개념 (근거 헤더용)")
    parser.add_argument("--rationale", help="선정 근거 (근거 헤더용)")
    args = parser.parse_args(argv)

    try:
        draft_path = Path(args.draft)
        if not draft_path.exists():
            print(f"[thumbnail-prompt] 초안이 없습니다: {draft_path}", file=sys.stderr)
            return 2
        colors = load_category_colors(str(_find_guides_dir()))
        if args.category not in colors:
            valid = ", ".join(sorted(colors))
            raise SpecError(
                f"카테고리 '{args.category}' 가 thumbnails.md §5.1 에 없습니다. "
                f"유효 카테고리: {valid}. 새 카테고리면 THUMBNAIL_COLORS 표에 한 줄 추가하세요."
            )
        prompt = build_prompt(
            colors[args.category],
            args.category,
            args.object_text,
            args.concept,
            args.rationale,
        )

        out_dir = _find_repo_root() / "thumbnails"
        out_dir.mkdir(exist_ok=True)
        slug = _slug(args.draft)
        prompt_path = out_dir / f"{slug}.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2

    print(f"프롬프트를 썼습니다: {prompt_path}")
    if not args.object_text:
        print(
            "맨 위 {{OBJECT}}·{{CONCEPT}}·{{RATIONALE}} 를 채운 뒤 (초안을 읽고 §2.4 절차로) "
            "GPT 에 붙여넣으세요 (게이트 ③)."
        )
    else:
        print("GPT 에 붙여넣으세요 (게이트 ③). 산출물은 make thumbnail-check 로 검사합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
