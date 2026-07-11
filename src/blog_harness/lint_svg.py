"""다이어그램 SVG 린터 — guides/RULES.md 의 SVG-01~09 를 강제한다.

이 저장소의 심장이다. 179개 다이어그램을 그리며 축적한 규칙을 매번 손으로 잡던 것을,
규칙 ID를 출력하는 자동 검사로 바꾼다. RULES.md 가 계약서다 — 규칙을 지어내지 않는다.

설계 경계 (사용자 확정):
  - **자라는 목록은 문서에서 파싱한다** — Core 팔레트(diagram-system.md §2.2). 이게
    lint_svg 의 유일한 doc-parse 이며 `--palette-report` 에서만 쓴다.
  - **물리·기하 상수는 코드 상수로 둔다** — 각 상수에 규칙 ID 주석을 달아 RULES.md 와
    동기화한다. 물리 상수를 산문에서 파싱하면 문서 오타가 린터를 죽이고, 파싱 코드가
    규칙보다 복잡해진다.
  - 파싱 실패는 SpecError 로 — 어느 파일의 무엇이 잘못됐고 어떻게 고치는지 담는다.

최우선 제약: **false positive 금지.** 멀쩡한 것을 잡으면 사람이 린터를 무시하고, 그 순간
하네스는 죽는다.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"

# ── 수준 매핑 ──────────────────────────────────────────────────────────────
# guides/RULES.md § "수준" 및 각 규칙 헤더의 (ERROR/WARN/INFO) 와 동기화할 것
ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

# ── 물리·기하 상수 (RULES.md 와 동기화할 것) ───────────────────────────────
# guides/RULES.md § SVG-01 — viewBox 폭 상한
CANVAS_MAX_WIDTH = 900

# guides/RULES.md § SVG-02 — 루트 font-family
FONT_FAMILY = "Noto Sans CJK KR, sans-serif"

# guides/RULES.md § SVG-05 — 골격 divider 고정 좌표 / diagram-patterns/skeleton-layer.md §2
#   (밴드 y, 기대 y, x_left, x_right)
SKELETON_DIVIDERS = (
    ("divider1", 250, 90, 690),  # User/Kernel
    ("divider2", 350, 30, 690),  # S/W ↔ H/W
)
SKELETON_BAND_TOL = 6  # y 가 250±6 또는 350±6 이면 골격으로 본다
SKELETON_MIN_LEN = 400  # 길이 400 이상인 수평선만 골격 divider 로 본다

# guides/RULES.md § SVG-07 — 사선·곡선 화살촉 공식 / diagram-patterns/arrowhead.md §3
ARROW_TIP_DIST = 12  # 팁 ~ 밑변중점 거리
ARROW_HALF_WIDTH = 5  # 밑변 반폭
ARROW_TOL = 1.5  # 허용 오차 (px)

# guides/RULES.md § SVG-08 — 팔레트 비교 시 색이 아닌 값은 건너뛴다
_NON_COLOR = {"none", "transparent", "currentcolor", "inherit", ""}

# guides/RULES.md § SVG-09 — 파일명: 소문자·언더스코어·숫자만
_FILENAME_RE = re.compile(r"^[a-z0-9_]+$")


class SpecError(Exception):
    """명세 문서를 파싱하지 못했을 때 — 파일/원인/수정법을 담는다."""


@dataclass(frozen=True)
class Finding:
    level: str
    rule_id: str
    message: str


# ── SVG-03: 금지 유니코드 ──────────────────────────────────────────────────
# guides/RULES.md § SVG-03 — 아래첨자·위첨자·⋮ 는 rsvg-convert 에서 tofu(□)로 깨진다
def _build_forbidden_unicode() -> dict[str, str]:
    """금지 문자 → 대체 문자. 대체는 NFKC 정규화, ⋮ 만 특례."""
    chars: list[str] = []
    chars += [chr(0x2080 + i) for i in range(10)]  # ₀₁₂₃₄₅₆₇₈₉
    chars += ["⁰", "¹", "²", "³"]  # ⁰¹²³
    chars += [chr(0x2074 + i) for i in range(6)]  # ⁴⁵⁶⁷⁸⁹
    chars += ["⋮"]  # ⋮
    mapping: dict[str, str] = {}
    for ch in chars:
        if ch == "⋮":
            mapping[ch] = "..."
        else:
            nfkc = unicodedata.normalize("NFKC", ch)
            mapping[ch] = nfkc if nfkc != ch else "?"
    return mapping


FORBIDDEN_UNICODE = _build_forbidden_unicode()


# ── Core 팔레트 로더 (유일한 doc-parse, --palette-report 전용) ──────────────
def _find_guides_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "guides" / "diagram-system.md"
        if candidate.exists():
            return parent / "guides"
    raise SpecError(
        "guides/diagram-system.md 를 찾지 못했습니다. "
        "저장소 루트에서 실행하고 guides/ 디렉토리가 있는지 확인하세요."
    )


def _extract_section(text: str, header: str) -> str:
    """`header` 로 시작하는 줄부터 다음 동급/상위 헤더 전까지."""
    lines = text.splitlines()
    out: list[str] = []
    capturing = False
    for line in lines:
        if line.startswith(header):
            capturing = True
            continue
        if capturing and re.match(r"^#{1,3} ", line):
            break
        if capturing:
            out.append(line)
    return "\n".join(out)


@lru_cache(maxsize=None)
def load_core_palette(guides_dir: str) -> frozenset[str]:
    """diagram-system.md §2.2 표의 값 열에서 hex/`white` 를 파싱한다 (소문자 정규화)."""
    doc = Path(guides_dir) / "diagram-system.md"
    if not doc.exists():
        raise SpecError(f"{doc} 가 없습니다 — Core 팔레트를 읽을 수 없습니다.")
    section = _extract_section(doc.read_text(encoding="utf-8"), "### 2.2")
    if not section:
        raise SpecError(
            f"{doc} 에서 '### 2.2 색 팔레트' 섹션을 찾지 못했습니다. "
            "헤더가 '### 2.2' 로 시작하는지 확인하세요."
        )
    palette: set[str] = set()
    for token in re.findall(r"`([^`]+)`", section):
        t = token.strip().lower()
        if re.fullmatch(r"#[0-9a-f]{3,6}", t) or t == "white":
            palette.add(t)
    if not palette:
        raise SpecError(
            f"{doc} §2.2 팔레트 표에서 색을 하나도 읽지 못했습니다. "
            "값 열이 `#rrggbb` 또는 `white` 형식의 백틱 코드스팬인지 확인하세요."
        )
    return frozenset(palette)


# ── 헬퍼 ───────────────────────────────────────────────────────────────────
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _num(value: str | None) -> float | None:
    if value is None:
        return None
    m = re.match(r"\s*([-+]?\d*\.?\d+)", value)
    return float(m.group(1)) if m else None


def _fmt(x: float) -> str:
    return f"{x:g}"


# ── 원문 기반 체크 (XML 파싱 전) ───────────────────────────────────────────
def check_forbidden_unicode(text: str) -> list[Finding]:
    """SVG-03 — 원문에 금지 유니코드가 있으면 ERROR. 대체 문자를 제시한다."""
    findings: list[Finding] = []
    for ch, repl in FORBIDDEN_UNICODE.items():
        if ch in text:
            cp = f"U+{ord(ch):04X}"
            findings.append(
                Finding(ERROR, "SVG-03", f"금지 문자 '{ch}'({cp}). '{repl}' 로 대체.")
            )
    return findings


def check_xml_comments(text: str) -> list[Finding]:
    """SVG-04 — <!-- --> 안에 '--' 가 있으면 SVG 파싱 에러를 유발한다."""
    findings: list[Finding] = []
    for inner in re.findall(r"<!--(.*?)-->", text, re.DOTALL):
        if "--" in inner:
            findings.append(
                Finding(ERROR, "SVG-04", "XML 주석 안에 '--' 가 있어 SVG 파싱 에러를 유발한다.")
            )
    return findings


def check_filename(path: str) -> list[Finding]:
    """SVG-09 — 파일명은 소문자·언더스코어·숫자만 (WARN)."""
    p = Path(path)
    if p.suffix.lower() != ".svg":
        return []
    if not _FILENAME_RE.fullmatch(p.stem):
        return [
            Finding(WARN, "SVG-09", f"파일명 '{p.stem}' — 소문자·언더스코어·숫자만 쓴다.")
        ]
    return []


# ── 구조 체크 (XML 파싱 후) ────────────────────────────────────────────────
def check_viewbox(root: ET.Element) -> list[Finding]:
    """SVG-01 — viewBox 폭 ≤ 900."""
    width: float | None = None
    vb = root.get("viewBox")
    if vb:
        parts = re.split(r"[\s,]+", vb.strip())
        if len(parts) == 4:
            width = _num(parts[2])
    if width is None:
        width = _num(root.get("width"))
    if width is not None and width > CANVAS_MAX_WIDTH:
        return [
            Finding(
                ERROR,
                "SVG-01",
                f"viewBox 폭 {_fmt(width)} > {CANVAS_MAX_WIDTH}. "
                f"콘텐츠에 맞춰 ≤{CANVAS_MAX_WIDTH} 로.",
            )
        ]
    return []


def check_font(root: ET.Element) -> list[Finding]:
    """SVG-02 — 루트 font-family == 'Noto Sans CJK KR, sans-serif'."""
    actual = (root.get("font-family") or "").strip()
    if actual != FONT_FAMILY:
        shown = actual or "(없음)"
        return [
            Finding(ERROR, "SVG-02", f'루트 font-family 가 "{shown}" — "{FONT_FAMILY}" 여야 한다.')
        ]
    return []


@dataclass(frozen=True)
class _Divider:
    name: str
    y: float
    x_left: float
    x_right: float
    exp_y: int
    exp_left: int
    exp_right: int


def _detect_dividers(root: ET.Element) -> list[_Divider]:
    """골격 divider: 수평선 중 y 가 250±6/350±6 이고 길이 ≥ 400 인 것."""
    dividers: list[_Divider] = []
    for el in root.iter():
        if _local(el.tag) != "line":
            continue
        x1, y1 = _num(el.get("x1")), _num(el.get("y1"))
        x2, y2 = _num(el.get("x2")), _num(el.get("y2"))
        if None in (x1, y1, x2, y2):
            continue
        if abs(y1 - y2) > 0.5:  # 수평선만
            continue
        if abs(x2 - x1) < SKELETON_MIN_LEN:
            continue
        y = y1
        for name, exp_y, exp_left, exp_right in SKELETON_DIVIDERS:
            if abs(y - exp_y) <= SKELETON_BAND_TOL:
                dividers.append(
                    _Divider(name, y, min(x1, x2), max(x1, x2), exp_y, exp_left, exp_right)
                )
                break
    return dividers


def check_skeleton_coords(dividers: list[_Divider]) -> list[Finding]:
    """SVG-05 — 탐지된 골격 divider 가 규격 좌표와 어긋나면 ERROR."""
    findings: list[Finding] = []
    for d in dividers:
        bad = (
            abs(d.y - d.exp_y) > 0.5
            or abs(d.x_left - d.exp_left) > 0.5
            or abs(d.x_right - d.exp_right) > 0.5
        )
        if bad:
            findings.append(
                Finding(
                    ERROR,
                    "SVG-05",
                    f"골격 {d.name} 좌표 어긋남: 실제 y={_fmt(d.y)} x {_fmt(d.x_left)}→"
                    f"{_fmt(d.x_right)}, 기대 y={d.exp_y} x {d.exp_left}→{d.exp_right}.",
                )
            )
    return findings


def check_sockets(root: ET.Element, dividers: list[_Divider]) -> list[Finding]:
    """SVG-06 — 골격 divider 를 가로지르는 타원/원 금지. cy + ry ≤ divider_y."""
    if not dividers:
        return []
    shapes: list[tuple[float, float]] = []  # (cy, ry)
    for el in root.iter():
        tag = _local(el.tag)
        if tag == "ellipse":
            cy, ry = _num(el.get("cy")), _num(el.get("ry"))
        elif tag == "circle":
            cy, ry = _num(el.get("cy")), _num(el.get("r"))
        else:
            continue
        if cy is None or ry is None:
            continue
        shapes.append((cy, ry))

    findings: list[Finding] = []
    for d in dividers:
        for cy, ry in shapes:
            top, bottom = cy - ry, cy + ry
            if top < d.y < bottom:  # 엄격 비교 — 정확히 접함(bottom==y)은 통과
                penetration = bottom - d.y
                suggested = d.y - ry
                findings.append(
                    Finding(
                        ERROR,
                        "SVG-06",
                        f"타원이 divider(y={_fmt(d.y)})를 {_fmt(penetration)}px 침범. "
                        f"cy={_fmt(cy)} 를 {_fmt(suggested)} 로 (cy = divider_y - ry)",
                    )
                )
    return findings


def _polygon_points(el: ET.Element) -> list[tuple[float, float]]:
    nums = re.findall(r"[-+]?\d*\.?\d+", el.get("points") or "")
    if len(nums) % 2 != 0:
        return []
    vals = [float(n) for n in nums]
    return [(vals[i], vals[i + 1]) for i in range(0, len(vals), 2)]


def check_arrowheads(root: ET.Element) -> list[Finding]:
    """SVG-07 — 사선·곡선 화살촉이 §3.2 공식과 어긋나면 WARN.

    3점 polygon 만 검사. 밑변이 축정렬(수평·수직 표준 화살촉)이면 통과.
    """
    findings: list[Finding] = []
    for el in root.iter():
        if _local(el.tag) != "polygon":
            continue
        pts = _polygon_points(el)
        if len(pts) != 3:  # 3점이 아니면 화살촉이 아니다
            continue

        # 축정렬 밑변(두 점이 x 또는 y 공유) → 표준 화살촉, 통과
        axis_aligned = any(
            abs(a[0] - b[0]) < 0.5 or abs(a[1] - b[1]) < 0.5
            for a, b in ((pts[0], pts[1]), (pts[0], pts[2]), (pts[1], pts[2]))
        )
        if axis_aligned:
            continue

        best = None  # (|dist-12|+|half-5|, dist, half)
        ok = False
        for i in range(3):
            tip = pts[i]
            b1, b2 = pts[(i + 1) % 3], pts[(i + 2) % 3]
            mid = ((b1[0] + b2[0]) / 2, (b1[1] + b2[1]) / 2)
            dist = math.hypot(tip[0] - mid[0], tip[1] - mid[1])
            half = math.hypot(b1[0] - b2[0], b1[1] - b2[1]) / 2
            err = abs(dist - ARROW_TIP_DIST) + abs(half - ARROW_HALF_WIDTH)
            if best is None or err < best[0]:
                best = (err, dist, half)
            if abs(dist - ARROW_TIP_DIST) <= ARROW_TOL and abs(half - ARROW_HALF_WIDTH) <= ARROW_TOL:
                ok = True
                break
        if not ok and best is not None:
            _, dist, half = best
            findings.append(
                Finding(
                    WARN,
                    "SVG-07",
                    f"사선 화살촉이 §3.2 공식과 어긋남 (팁~밑변중점 {dist:.1f}≠{ARROW_TIP_DIST}, "
                    f"반폭 {half:.1f}≠{ARROW_HALF_WIDTH}). arrowhead.md §3 으로 재계산.",
                )
            )
    return findings


def collect_palette(root: ET.Element, core: frozenset[str]) -> Counter[str]:
    """SVG-08 — Core 밖 색을 누적 카운트한다 (INFO, --palette-report 전용)."""
    counts: Counter[str] = Counter()
    for el in root.iter():
        for attr in ("fill", "stroke"):
            raw = el.get(attr)
            if raw is None:
                continue
            val = raw.strip().lower()
            if val in _NON_COLOR or val.startswith("url("):
                continue
            if val in core:
                continue
            counts[val] += 1
    return counts


# ── 오케스트레이션 ─────────────────────────────────────────────────────────
def lint_svg_text(text: str, path: str = "mem.svg") -> list[Finding]:
    """한 SVG 텍스트에 모든 체크를 적용한다. 테스트 코어.

    SVG-08(팔레트)은 여기서 출력하지 않는다 — 노이즈 방지, --palette-report 전용.
    """
    findings: list[Finding] = []
    # 원문 기반 (XML 파싱이 깨져도 동작)
    findings += check_forbidden_unicode(text)
    findings += check_xml_comments(text)
    findings += check_filename(path)

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        if not any(f.rule_id == "SVG-04" for f in findings):
            findings.append(Finding(ERROR, "PARSE", f"XML 파싱 실패: {e}"))
        return findings

    findings += check_viewbox(root)
    findings += check_font(root)
    dividers = _detect_dividers(root)
    findings += check_skeleton_coords(dividers)
    findings += check_sockets(root, dividers)
    findings += check_arrowheads(root)
    return findings


def lint_file(path: Path) -> list[Finding]:
    return lint_svg_text(path.read_text(encoding="utf-8"), str(path))


def iter_svg_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out += sorted(p.rglob("*.svg"))
        elif p.suffix.lower() == ".svg":
            out.append(p)
    # 중복 제거, 정렬
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def palette_report(paths: list[str]) -> int:
    """파일 횡단 팔레트 집계. 3회 이상은 승격 검토. 항상 exit 0 (INFO)."""
    core = load_core_palette(str(_find_guides_dir()))
    totals: Counter[str] = Counter()
    files = iter_svg_files(paths)
    for path in files:
        try:
            root = ET.fromstring(path.read_text(encoding="utf-8"))
        except ET.ParseError:
            continue
        totals += collect_palette(root, core)

    print(f"미등록 색 사용 현황 ({len(files)}개 파일):")
    if not totals:
        print("  (없음 — 전부 Core 팔레트)")
        return 0
    for color, count in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])):
        note = "← 3회 이상. 승격 검토" if count >= 3 else "← 단발"
        print(f"  {color:<10} {count:>3}회   {note}")
    return 0


def _run_lint(paths: list[str], strict: bool) -> int:
    files = iter_svg_files(paths)
    if not files:
        print("검사할 SVG 파일이 없습니다.", file=sys.stderr)
        return 0

    total_error = total_warn = 0
    for path in files:
        findings = lint_file(path)
        if not findings:
            continue
        print(path)
        for f in findings:
            print(f"  [{f.level}] {f.rule_id}: {f.message}")
            if f.level == ERROR:
                total_error += 1
            elif f.level == WARN:
                total_warn += 1

    if total_error or total_warn:
        print(f"\n{len(files)}개 검사 — ERROR {total_error}, WARN {total_warn}")
    if total_error:
        return 1
    if strict and total_warn:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint-svg", description="다이어그램 SVG 린터 (guides/RULES.md SVG-01~09)"
    )
    parser.add_argument("paths", nargs="+", help="SVG 파일 또는 디렉토리(재귀)")
    parser.add_argument("--strict", action="store_true", help="WARN 도 실패로 처리")
    parser.add_argument(
        "--palette-report", action="store_true", help="Core 밖 색 누적 집계 (SVG-08)"
    )
    args = parser.parse_args(argv)

    try:
        if args.palette_report:
            return palette_report(args.paths)
        return _run_lint(args.paths, args.strict)
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
