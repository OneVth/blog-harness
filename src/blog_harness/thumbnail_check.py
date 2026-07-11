"""썸네일 검증기 — guides/RULES.md THUMB-01~05 를 강제한다.

GPT 가 만든 썸네일(`thumbnails/<slug>.png`)이 규격에 맞는지 기계로 검사하고, **150px
다운스케일을 실제로 생성한다**(THUMB-05). 가이드 1항이 "150px 로 줄여도 무엇인지
보이는가" 인데, 육안으로 상상하지 않는다 — 실제로 만들어서 보여준다. 그 이미지가
블라인드 테스트(§8.1)의 입력이 된다.

기계가 잡는 것만 잡는다: 비율·해상도·색상 수·배경 밝기. 개념 전달 여부는 기계가 못
잡는다 — 블라인드 테스트(사람/다른 세션 Claude)의 몫이다 (RULES.md "검사하지 않는 것").

설계 경계 ([[parse-vs-constant-boundary]]): 규격은 물리·기하값이라 문서 파싱이 아니라
규칙 ID 주석 단 상수로 둔다. THUMB-03 임계값만은 **실측으로 정한다** — 실제 썸네일을
여러 장 돌려보고 조정한다. 추측으로 박으면 false positive 가 나고, 그 순간 사람이
린터를 무시한다. 지금은 느슨한 기본값(8) + `--max-colors` 로 조정 가능하게 둔다.

lint_svg.py 의 Finding / 보고 루프 / exit code 관례를 복제한다 (공유 모듈 없음).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

# ── 수준 (guides/RULES.md § "수준" 및 THUMB-NN 헤더와 동기화) ────────────────
ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

# ── 상수 (RULES.md/thumbnails.md 와 동기화) ─────────────────────────────────
# guides/RULES.md § THUMB-02 — 허용 해상도.
_VALID_RESOLUTIONS = frozenset({(1024, 1024), (2048, 2048)})
# guides/RULES.md § THUMB-03 — dominant color 개수 상한. 실측 전 느슨한 기본값.
DEFAULT_MAX_COLORS = 8
# THUMB-03 — dominant 으로 셀 최소 점유율. 안티앨리어싱 잡색을 걸러낸다.
_COLOR_COVERAGE_FLOOR = 0.03
# THUMB-03 — 색상 수 셀 때 잡음을 줄이는 다운샘플·양자화 크기.
_QUANTIZE_SAMPLE = 128
_QUANTIZE_COLORS = 64
# guides/RULES.md § THUMB-04 — 가장자리 평균 휘도 하한 (0~1). 밑돌면 배경이 어둡다.
_MIN_EDGE_LUMINANCE = 0.5
# guides/RULES.md § THUMB-05 — 다운스케일 목표 변.
_DOWNSCALE = 150


@dataclass(frozen=True)
class Finding:
    level: str
    rule_id: str
    message: str


class SpecError(Exception):
    """명세 문서·입력을 파싱하지 못했을 때 — 파일/원인/수정법을 담는다."""


def _find_guides_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "guides" / "thumbnails.md"
        if candidate.exists():
            return parent / "guides"
    raise SpecError(
        "guides/thumbnails.md 를 찾지 못했습니다. "
        "저장소 루트에서 실행하고 guides/ 디렉토리가 있는지 확인하세요."
    )


# ── 순수 검사 (테스트 코어) — PIL Image 를 받는다 ──────────────────────────
def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def check_ratio(img) -> list[Finding]:
    """THUMB-01 — 1:1 이 아니면 ERROR."""
    w, h = img.size
    if w != h:
        return [Finding(ERROR, "THUMB-01", f"비율이 1:1 이 아닙니다 ({w}×{h}). 정사각형이어야 한다.")]
    return []


def check_resolution(img) -> list[Finding]:
    """THUMB-02 — 1024²·2048² 이 아니면 ERROR."""
    if img.size not in _VALID_RESOLUTIONS:
        w, h = img.size
        allowed = " 또는 ".join(f"{a}×{b}" for a, b in sorted(_VALID_RESOLUTIONS))
        return [Finding(ERROR, "THUMB-02", f"해상도 {w}×{h} — {allowed} 여야 한다.")]
    return []


def check_colors(img, max_colors: int) -> list[Finding]:
    """THUMB-03 — 점유율 기준 dominant color 가 max_colors 초과면 ERROR (무지개 금지)."""
    small = img.convert("RGB").resize((_QUANTIZE_SAMPLE, _QUANTIZE_SAMPLE))
    q = small.quantize(colors=_QUANTIZE_COLORS)
    total = _QUANTIZE_SAMPLE * _QUANTIZE_SAMPLE
    counts = q.getcolors(total) or []
    dominant = [c for c, _ in counts if c / total >= _COLOR_COVERAGE_FLOOR]
    n = len(dominant)
    if n > max_colors:
        return [
            Finding(
                ERROR,
                "THUMB-03",
                f"dominant color {n}개 (상한 {max_colors}). 무지개 금지 — 주색상 1개 원칙.",
            )
        ]
    return []


def check_brightness(img) -> list[Finding]:
    """THUMB-04 — 가장자리 평균 휘도가 기준 미만이면 WARN (배경이 어두우면 오브젝트가 묻힌다)."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    samples: list[float] = []
    for x in range(w):
        samples.append(_luminance(px[x, 0]))
        samples.append(_luminance(px[x, h - 1]))
    for y in range(h):
        samples.append(_luminance(px[0, y]))
        samples.append(_luminance(px[w - 1, y]))
    mean = sum(samples) / len(samples)
    if mean < _MIN_EDGE_LUMINANCE:
        return [
            Finding(
                WARN,
                "THUMB-04",
                f"가장자리 평균 휘도 {mean:.2f} < {_MIN_EDGE_LUMINANCE:.2f}. "
                "배경이 어두워 오브젝트가 묻힐 수 있다.",
            )
        ]
    return []


def check_image(img, max_colors: int) -> list[Finding]:
    """THUMB-01~04 를 모아 돌린다. 순수 함수 — IO 없음."""
    findings: list[Finding] = []
    findings += check_ratio(img)
    findings += check_resolution(img)
    findings += check_colors(img, max_colors)
    findings += check_brightness(img)
    return findings


# ── 150px 생성 (THUMB-05, INFO) ────────────────────────────────────────────
def _downscale_slug(path: Path) -> str:
    """입력 stem 에서 `.150` 을 떼어 slug 을 얻는다 (이미 .150.png 를 넣어도 멱등)."""
    stem = path.stem
    return stem[:-4] if stem.endswith(".150") else stem


def generate_150(img, out_path: Path) -> Path:
    """THUMB-05 — 150px 다운스케일을 out_path 에 쓴다. 종횡비 유지."""
    thumb = img.convert("RGB")
    thumb.thumbnail((_DOWNSCALE, _DOWNSCALE))
    thumb.save(out_path)
    return out_path


# ── CLI ────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="thumbnail-check",
        description="썸네일 검사 + 150px 생성 (guides/RULES.md THUMB-01~05)",
    )
    parser.add_argument("thumb", help="썸네일 PNG (예: thumbnails/foo.png)")
    parser.add_argument(
        "--max-colors",
        type=int,
        default=DEFAULT_MAX_COLORS,
        help=f"THUMB-03 dominant color 상한 (기본 {DEFAULT_MAX_COLORS}, 실측으로 조정)",
    )
    parser.add_argument("--strict", action="store_true", help="WARN 도 실패로 처리")
    args = parser.parse_args(argv)

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        print(
            "[thumbnail-check] Pillow 가 필요합니다. `uv sync --extra thumbnail` "
            "(또는 dev 그룹 설치) 로 설치하세요.",
            file=sys.stderr,
        )
        return 2

    try:
        thumb_path = Path(args.thumb)
        if not thumb_path.exists():
            print(f"[thumbnail-check] 파일이 없습니다: {thumb_path}", file=sys.stderr)
            return 2
        try:
            img = Image.open(thumb_path)
            img.load()
        except (UnidentifiedImageError, OSError) as e:
            raise SpecError(
                f"{thumb_path} 를 이미지로 열지 못했습니다 ({e}). PNG 인지 확인하세요."
            ) from e

        findings = check_image(img, args.max_colors)

        out_path = thumb_path.with_name(f"{_downscale_slug(thumb_path)}.150.png")
        generate_150(img, out_path)
        findings.append(Finding(INFO, "THUMB-05", f"150px 생성: {out_path}"))
    except SpecError as e:
        print(f"[SpecError] {e}", file=sys.stderr)
        return 2

    print(thumb_path)
    total_error = total_warn = 0
    for f in findings:
        print(f"  [{f.level}] {f.rule_id}: {f.message}")
        if f.level == ERROR:
            total_error += 1
        elif f.level == WARN:
            total_warn += 1

    print(f"\nERROR {total_error}, WARN {total_warn}")
    print("150px 이미지를 블라인드 테스트에 던지세요 (thumbnails.md §8.1).")
    if total_error:
        return 1
    if args.strict and total_warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
