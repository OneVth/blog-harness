"""thumbnail_check 테스트.

기계 검사(THUMB-01~05)만 검증한다. 개념 전달 여부는 블라인드 테스트의 몫이라 여기서
검사하지 않는다. 합성 이미지로 각 규칙을 켠다.
"""

import pytest

Image = pytest.importorskip("PIL.Image")

from blog_harness.thumbnail_check import (  # noqa: E402
    check_brightness,
    check_colors,
    check_image,
    check_ratio,
    check_resolution,
    generate_150,
    main,
)

DEFAULT_MAX = 8


def _solid(size, color):
    return Image.new("RGB", size, color)


def _rainbow(size):
    """4×4 = 16개 뚜렷한 색 블록. dominant color 16개 (> 상한 8)."""
    img = Image.new("RGB", size)
    w, h = size
    cw, ch = w // 4, h // 4
    palette = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
        (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
        (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
        (255, 128, 0), (128, 255, 0), (0, 128, 255), (200, 200, 200),
    ]
    for i, col in enumerate(palette):
        x, y = (i % 4) * cw, (i // 4) * ch
        for xx in range(x, x + cw):
            for yy in range(y, y + ch):
                img.putpixel((xx, yy), col)
    return img


# ── THUMB-01 비율 ──────────────────────────────────────────────────────────
def test_ratio_non_square_errors():
    fs = check_ratio(_solid((1000, 800), (200, 200, 200)))
    assert [f.rule_id for f in fs] == ["THUMB-01"]
    assert fs[0].level == "ERROR"


def test_ratio_square_ok():
    assert check_ratio(_solid((1024, 1024), (200, 200, 200))) == []


# ── THUMB-02 해상도 ────────────────────────────────────────────────────────
def test_resolution_wrong_errors():
    fs = check_resolution(_solid((512, 512), (200, 200, 200)))
    assert [f.rule_id for f in fs] == ["THUMB-02"]


def test_resolution_1024_and_2048_ok():
    assert check_resolution(_solid((1024, 1024), (1, 1, 1))) == []
    assert check_resolution(_solid((2048, 2048), (1, 1, 1))) == []


# ── THUMB-03 색상 수 ───────────────────────────────────────────────────────
def test_colors_rainbow_errors():
    fs = check_colors(_rainbow((1024, 1024)), DEFAULT_MAX)
    assert [f.rule_id for f in fs] == ["THUMB-03"]


def test_colors_single_ok():
    assert check_colors(_solid((1024, 1024), (200, 190, 150)), DEFAULT_MAX) == []


def test_colors_threshold_tunable():
    """상한을 20으로 올리면 무지개도 통과한다 (실측 조정 여지)."""
    assert check_colors(_rainbow((1024, 1024)), 20) == []


# ── THUMB-04 배경 밝기 ─────────────────────────────────────────────────────
def test_brightness_dark_warns():
    fs = check_brightness(_solid((1024, 1024), (30, 30, 30)))
    assert [f.rule_id for f in fs] == ["THUMB-04"]
    assert fs[0].level == "WARN"


def test_brightness_light_ok():
    assert check_brightness(_solid((1024, 1024), (220, 210, 190))) == []


# ── THUMB-05 150px 생성 ────────────────────────────────────────────────────
def test_generate_150_creates_file(tmp_path):
    out = tmp_path / "foo.150.png"
    generate_150(_solid((1024, 1024), (200, 200, 200)), out)
    assert out.exists()
    assert max(Image.open(out).size) == 150


# ── check_image 집계 ───────────────────────────────────────────────────────
def test_check_image_clean_thumbnail():
    assert check_image(_solid((1024, 1024), (200, 190, 150)), DEFAULT_MAX) == []


# ── main end-to-end ────────────────────────────────────────────────────────
def test_main_clean_exit0_and_generates_150(tmp_path):
    p = tmp_path / "foo.png"
    _solid((1024, 1024), (200, 190, 150)).save(p)
    assert main([str(p)]) == 0
    assert (tmp_path / "foo.150.png").exists()


def test_main_bad_ratio_exit1(tmp_path):
    p = tmp_path / "bad.png"
    _solid((1000, 800), (200, 190, 150)).save(p)
    assert main([str(p)]) == 1
    assert (tmp_path / "bad.150.png").exists()  # 150px 는 실패해도 생성 (보고 대상)


def test_main_missing_file_exit2(tmp_path):
    assert main([str(tmp_path / "nope.png")]) == 2
