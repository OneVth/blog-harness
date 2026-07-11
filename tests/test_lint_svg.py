"""lint_svg 양방향 테스트.

거짓말하는 하네스는 없느니만 못하다 — false negative(놓침)와 false positive(오탐)를
모두 검증한다. 최우선은 오탐 방지: 멀쩡한 SVG 는 조용히 통과해야 한다.
"""

from pathlib import Path

import pytest

from blog_harness.lint_svg import (
    load_core_palette,
    _find_guides_dir,
    lint_file,
    lint_svg_text,
    main,
)

REPO = Path(__file__).resolve().parents[1]
FONT = "Noto Sans CJK KR, sans-serif"
DIVIDER1 = '<line x1="90" y1="250" x2="690" y2="250" stroke="#444" stroke-width="1.5"/>'


def svg(body: str = "", viewbox: str = "0 0 720 480", font: str = FONT) -> str:
    return (
        f'<svg viewBox="{viewbox}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="{font}">{body}</svg>'
    )


def ids(findings) -> list[str]:
    return [f.rule_id for f in findings]


def levels(findings) -> set[str]:
    return {f.level for f in findings}


# ── false positive 방지 (조용히 통과해야 함) ──────────────────────────────
def test_template_lints_clean():
    """규격 골격 템플릿은 findings == [] 여야 한다 (회귀 기준)."""
    template = REPO / "diagrams" / "_template" / "layer_skeleton.svg"
    assert lint_file(template) == []


def test_socket_touching_exactly_passes():
    """cy = divider_y - ry 를 정확히 지킨 소켓은 통과 (bottom == divider)."""
    body = DIVIDER1 + '<ellipse cx="300" cy="234" rx="40" ry="16"/>'
    assert lint_svg_text(svg(body)) == []


def test_ellipse_far_from_divider_passes():
    """divider 에서 먼 타원은 검사 대상이 아니다."""
    body = DIVIDER1 + '<ellipse cx="300" cy="100" rx="40" ry="16"/>'
    assert lint_svg_text(svg(body)) == []


def test_non_skeleton_diagram_ignores_socket_rule():
    """골격을 안 쓰는 다이어그램에 골격 규칙을 들이대지 않는다."""
    body = '<ellipse cx="300" cy="250" rx="40" ry="30"/>'  # divider 없음
    findings = lint_svg_text(svg(body))
    assert "SVG-05" not in ids(findings)
    assert "SVG-06" not in ids(findings)


def test_formula_arrowhead_passes():
    """arrowhead.md §3 공식대로 계산한 사선 화살촉은 통과."""
    body = '<polygon points="224,172 211.8,167.4 218.7,159.5" fill="#666"/>'
    assert lint_svg_text(svg(body)) == []


def test_standard_axis_arrowhead_passes():
    """수평·수직 표준 화살촉(축정렬 밑변)은 통과."""
    down = '<polygon points="194,140 206,140 200,151" fill="#666"/>'
    right = '<polygon points="200,135 200,145 210,140" fill="#666"/>'
    assert lint_svg_text(svg(down)) == []
    assert lint_svg_text(svg(right)) == []


def test_non_triangle_polygon_ignored():
    """3점이 아닌 polygon 은 화살촉이 아니므로 검사하지 않는다."""
    body = '<polygon points="10,10 90,10 90,90 10,90" fill="#666"/>'
    assert lint_svg_text(svg(body)) == []


def test_unregistered_color_is_not_error_or_warn():
    """미등록 색이 있어도 ERROR/WARN 이 아니다 (SVG-08 은 INFO, 일반 lint 무출력)."""
    body = '<rect x="10" y="10" width="40" height="20" fill="#b19cd9"/>'
    findings = lint_svg_text(svg(body))
    assert findings == []


# ── false negative 방지 (잡아야 함) ────────────────────────────────────────
def test_socket_straddling_center_flagged():
    """divider 가운데 걸친 소켓은 SVG-06 ERROR."""
    body = DIVIDER1 + '<ellipse cx="300" cy="250" rx="40" ry="30"/>'
    findings = lint_svg_text(svg(body))
    assert "SVG-06" in ids(findings)


def test_socket_1px_intrusion_flagged_with_fix_coord():
    """1px 침범 소켓 — 실제 버그. 에러 메시지에 고칠 좌표(234)가 있어야 한다."""
    body = DIVIDER1 + '<ellipse cx="300" cy="235" rx="40" ry="16"/>'
    findings = lint_svg_text(svg(body))
    socket = [f for f in findings if f.rule_id == "SVG-06"]
    assert socket, "1px 침범을 잡아야 한다"
    assert "234" in socket[0].message
    assert "1px" in socket[0].message


def test_circle_socket_intrusion_flagged():
    """circle(r) 도 divider 를 가로지르면 SVG-06."""
    body = DIVIDER1 + '<circle cx="300" cy="240" r="20"/>'  # bottom=260 > 250
    assert "SVG-06" in ids(lint_svg_text(svg(body)))


@pytest.mark.parametrize("char,repl", [("₁", "1"), ("²", "2"), ("⋮", "...")])
def test_forbidden_unicode_flagged(char, repl):
    """금지 유니코드는 SVG-03 ERROR + 대체 문자 제시."""
    body = f'<text x="10" y="20">x{char}</text>'
    findings = lint_svg_text(svg(body))
    svg03 = [f for f in findings if f.rule_id == "SVG-03"]
    assert svg03
    assert repl in svg03[0].message


def test_viewbox_over_900_flagged():
    """viewBox 폭 900 초과는 SVG-01 ERROR."""
    findings = lint_svg_text(svg(viewbox="0 0 1000 480"))
    assert "SVG-01" in ids(findings)


def test_viewbox_900_exactly_passes():
    """상한은 900 이다 (720 아님) — 900 정확히는 통과."""
    findings = lint_svg_text(svg(viewbox="0 0 900 480"))
    assert "SVG-01" not in ids(findings)


def test_wrong_font_flagged():
    """루트 font-family 가 규격과 다르면 SVG-02 ERROR."""
    findings = lint_svg_text(svg(font="Arial, sans-serif"))
    assert "SVG-02" in ids(findings)


def test_double_dash_in_comment_flagged():
    """XML 주석 안의 '--' 는 SVG-04 ERROR."""
    body = "<!-- 화살표 -- 추가 -->"
    findings = lint_svg_text(svg(body))
    assert "SVG-04" in ids(findings)


def test_eyeballed_arrowhead_warns():
    """눈대중 사선 화살촉은 SVG-07 WARN."""
    body = '<polygon points="100,100 150,140 130,180" fill="#666"/>'
    findings = lint_svg_text(svg(body))
    svg07 = [f for f in findings if f.rule_id == "SVG-07"]
    assert svg07
    assert svg07[0].level == "WARN"


def test_misplaced_divider_flagged():
    """골격 밴드 안이지만 규격 좌표와 어긋난 divider 는 SVG-05 ERROR."""
    body = '<line x1="90" y1="248" x2="690" y2="248" stroke="#444" stroke-width="1.5"/>'
    findings = lint_svg_text(svg(body))
    assert "SVG-05" in ids(findings)


def test_filename_uppercase_warns():
    """파일명에 대문자·하이픈이 있으면 SVG-09 WARN."""
    findings = lint_svg_text(svg(), path="Bad-Name.svg")
    assert "SVG-09" in ids(findings)


def test_filename_valid_passes():
    """소문자·언더스코어·숫자 파일명은 통과."""
    findings = lint_svg_text(svg(), path="context_switch_2.svg")
    assert "SVG-09" not in ids(findings)


# ── 팔레트 로더 (doc-parse) ────────────────────────────────────────────────
def test_core_palette_parsed_from_doc():
    """diagram-system.md §2.2 에서 Core 팔레트를 파싱한다."""
    core = load_core_palette(str(_find_guides_dir()))
    assert "#5db0d7" in core
    assert "white" in core
    assert "#444" in core


# ── main() exit 코드 ───────────────────────────────────────────────────────
def test_main_clean_returns_0():
    """규격 파일만 있으면 exit 0."""
    template = REPO / "diagrams" / "_template" / "layer_skeleton.svg"
    assert main([str(template)]) == 0


def test_main_error_returns_1(tmp_path):
    """ERROR 가 있으면 exit 1."""
    bad = tmp_path / "bad.svg"
    bad.write_text(svg(font="Arial"), encoding="utf-8")
    assert main([str(bad)]) == 1


def test_main_strict_promotes_warn(tmp_path):
    """WARN 만 있을 때 기본은 0, --strict 면 1."""
    warn = tmp_path / "warn_only.svg"
    warn.write_text(
        svg('<polygon points="100,100 150,140 130,180" fill="#666"/>'), encoding="utf-8"
    )
    assert main([str(warn)]) == 0
    assert main(["--strict", str(warn)]) == 1
