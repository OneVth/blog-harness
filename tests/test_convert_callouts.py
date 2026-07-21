"""convert_callouts 테스트 — 변환기가 틀리면 발행본이 깨진다.

CONV-01~06 계약을 양방향으로 검증한다. 특히 조용히 데이터를 깨는 함정
(코드 펜스·LaTeX·인라인 코드 안의 별표)을 집중적으로 잡는다.
"""

import pytest

from blog_harness.convert_callouts import (
    _find_guides_dir,
    convert_text,
    load_aliases,
    load_default_titles,
    main,
)

GUIDES = str(_find_guides_dir())
ALIASES = load_aliases(GUIDES)
TITLES = load_default_titles(GUIDES)


def conv(text: str) -> str:
    html, _ = convert_text(text, ALIASES, TITLES)
    return html


def warns(text: str) -> list[str]:
    _, findings = convert_text(text, ALIASES, TITLES)
    return [f.rule_id for f in findings]


# ── §7 실전 예시 5개 ────────────────────────────────────────────────────────
def test_example_note_definition():
    out = conv(
        "> [!note] B-Tree\n"
        "> B-Tree는 자식 노드를 여러 개 가질 수 있는 다진 트리이며,\n"
        "> 디스크 I/O를 최소화하기 위한 자료구조다."
    )
    assert '<blockquote class="markdown-callout markdown-callout-note">' in out
    assert '<p class="callout-title">B-Tree</p>' in out
    assert out.count("<p>") == 2  # 각 > 줄이 별도 <p>


def test_example_important_code():
    out = conv("> [!important] 시간복잡도\n> 평균 `O(log n)`, 최악 `O(log n)`.")
    assert "markdown-callout-important" in out
    assert '<p class="callout-title">시간복잡도</p>' in out
    assert out.count("<code>O(log n)</code>") == 2


def test_example_warning_code():
    out = conv("> [!warning] 자주 하는 실수\n> `==` 는 동등성, `===` 는 일치성 비교다.")
    assert "markdown-callout-warning" in out
    assert "<code>==</code>" in out
    assert "<code>===</code>" in out


def test_example_quote():
    out = conv("> [!quote] Donald Knuth\n> Premature optimization is the root of all evil.")
    assert "markdown-callout-quote" in out
    assert '<p class="callout-title">Donald Knuth</p>' in out


def test_example_success_default_title():
    out = conv("> [!success]\n> 결국 `HashTable`이 평균 O(1) 조회가 가능한 이유.")
    assert "markdown-callout-success" in out
    assert '<p class="callout-title">완료</p>' in out  # 타이틀 생략 → 기본
    assert "<code>HashTable</code>" in out


# ── alias 정규화 전체 (§4 표) ───────────────────────────────────────────────
def test_alias_table_has_27_entries():
    assert len(ALIASES) == 27


@pytest.mark.parametrize(("alias", "canonical"), sorted(ALIASES.items()))
def test_alias_normalizes(alias, canonical):
    out = conv(f"> [!{alias}] 제목\n> 본문")
    assert f"markdown-callout-{canonical}" in out


# ── 8종 기본 타이틀 (§3 표) ─────────────────────────────────────────────────
@pytest.mark.parametrize(("ctype", "title"), sorted(TITLES.items()))
def test_default_titles(ctype, title):
    out = conv(f"> [!{ctype}]\n> 본문")
    assert f'<p class="callout-title">{title}</p>' in out


# ── foldable 마커 무시 (§6) ─────────────────────────────────────────────────
def test_foldable_markers_ignored():
    assert '<p class="callout-title">펼침</p>' in conv("> [!tip]+ 펼침\n> x")
    assert '<p class="callout-title">접힘</p>' in conv("> [!note]- 접힘\n> x")
    # 마커 뒤 타이틀 생략 시 기본 타이틀
    assert '<p class="callout-title">팁</p>' in conv("> [!tip]+\n> x")


# ── 코드 펜스 보호 (CONV-01) — 가장 중요 ────────────────────────────────────
def test_code_fence_is_not_converted():
    text = "```markdown\n> [!warning] 코드 펜스 안\n> 변환되면 안 된다.\n```"
    out = conv(text)
    assert "<blockquote" not in out
    assert "markdown-callout" not in out
    assert out == text  # 펜스 안은 그대로


def test_callout_after_fence_still_converts():
    text = "```\n> [!note] 안\n```\n\n> [!tip] 밖\n> 본문"
    out = conv(text)
    assert out.count("<blockquote") == 1  # 펜스 밖 것만
    assert "markdown-callout-tip" in out


# ── LaTeX 보호 (CONV-03) — 검증된 버그 ──────────────────────────────────────
def test_latex_is_not_touched():
    out = conv("> [!note] 수식\n> LaTeX $a * b * c$ 안의 별표.")
    assert "$a * b * c$" in out
    assert "<em>" not in out


def test_latex_survives_with_other_markdown():
    out = conv("> [!note]\n> **굵게** 그리고 $x * y$ 그리고 `코드`.")
    assert "<strong>굵게</strong>" in out
    assert "$x * y$" in out
    assert "<code>코드</code>" in out
    assert "<em>" not in out


# ── 일반 blockquote 미변환 ──────────────────────────────────────────────────
def test_plain_blockquote_untouched():
    text = "> 그냥 인용문이다.\n> callout 이 아니다."
    out = conv(text)
    assert "markdown-callout" not in out
    assert out == text


# ── 중첩 callout 평문화 + 마커 제거 + 경고 (CONV-06) ────────────────────────
def test_nested_callout_flattened():
    text = "> [!note] 외부\n> 외부 본문\n> > [!tip] 내부 제목\n> > 내부 본문"
    out = conv(text)
    assert out.count("<blockquote") == 1  # outer 만
    assert "[!tip]" not in out  # 마커 제거
    assert "내부 제목" in out  # inner 는 평문으로 남는다
    assert "내부 본문" in out
    assert "CONV-06" in warns(text)


# ── HTML 이스케이프 ─────────────────────────────────────────────────────────
def test_html_escaped():
    out = conv("> [!note]\n> a < b && c > d")
    assert "a &lt; b &amp;&amp; c &gt; d" in out


# ── 연속 callout 병합 방지 ──────────────────────────────────────────────────
def test_adjacent_callouts_not_merged():
    text = "> [!note] A\n> x\n\n> [!tip] B\n> y"
    assert conv(text).count("<blockquote") == 2


def test_touching_callouts_not_merged():
    text = "> [!note] A\n> x\n> [!tip] B\n> y"
    out = conv(text)
    assert out.count("<blockquote") == 2
    assert "markdown-callout-note" in out
    assert "markdown-callout-tip" in out


# ── 인라인 코드 안의 별표는 기울임이 아니다 ─────────────────────────────────
def test_star_inside_code_not_italic():
    out = conv("> [!note]\n> `a * b * c` 는 코드다.")
    assert "<code>a * b * c</code>" in out
    assert "<em>" not in out


def test_bracket_inside_code_not_link():
    out = conv("> [!note]\n> `arr[0]` 접근.")
    assert "<code>arr[0]</code>" in out
    assert "<a href" not in out


# ── 인라인 변환 개별 ────────────────────────────────────────────────────────
def test_bold_italic_link():
    out = conv("> [!note]\n> **굵게** *기울임* [링크](https://x.com).")
    assert "<strong>굵게</strong>" in out
    assert "<em>기울임</em>" in out
    assert '<a href="https://x.com">링크</a>' in out


# ── 코드 펜스 밖 마크다운은 그대로 (callout 밖 미변환) ──────────────────────
def test_markdown_outside_callout_untouched():
    text = "## 헤더\n\n**굵게** 는 그대로.\n\n> [!note]\n> 본문"
    out = conv(text)
    assert "## 헤더" in out
    assert "**굵게** 는 그대로." in out  # callout 밖은 변환 안 함
    assert out.count("<blockquote") == 1


# ── main() exit code ────────────────────────────────────────────────────────
def test_main_stdout_returns_0(tmp_path, capsys):
    p = tmp_path / "in.md"
    p.write_text("> [!note] 제목\n> `코드`.", encoding="utf-8")
    assert main([str(p)]) == 0
    assert "<code>코드</code>" in capsys.readouterr().out


def test_main_output_file(tmp_path):
    p = tmp_path / "in.md"
    p.write_text("> [!tip] 제목\n> 본문", encoding="utf-8")
    out = tmp_path / "sub" / "out.md"
    assert main([str(p), "-o", str(out)]) == 0
    assert "markdown-callout-tip" in out.read_text(encoding="utf-8")


def test_main_check_warns_returns_1(tmp_path):
    p = tmp_path / "in.md"
    p.write_text("> [!note] 외부\n> > [!tip] 내부\n> > 내부 본문", encoding="utf-8")
    assert main(["--check", str(p)]) == 1


def test_main_check_clean_returns_0(tmp_path):
    p = tmp_path / "in.md"
    p.write_text("> [!note] 제목\n> 본문", encoding="utf-8")
    assert main(["--check", str(p)]) == 0


def test_main_missing_file_returns_2():
    assert main(["/nonexistent/nope.md"]) == 2


def test_frontmatter_stripped_from_output():
    """발행본에 카테고리·태그 frontmatter 가 새면 안 된다 (Tistory 오염 방지)."""
    text = "---\ncategory: DSA\ntags: [Array, 배열]\n---\n\n# 제목\n\n본문."
    out, _ = convert_text(text, ALIASES, TITLES)
    assert "category:" not in out
    assert "---" not in out.splitlines()[:2]
    assert out.lstrip().startswith("# 제목")


def test_no_frontmatter_body_unchanged():
    """frontmatter 가 없으면 본문을 건드리지 않는다."""
    text = "# 제목\n\n본문 그대로."
    out, _ = convert_text(text, ALIASES, TITLES)
    assert out.startswith("# 제목")


def test_diagram_ledger_stripped_from_output():
    """POST-15 결정 원장은 초안 전용 — 발행본에 새면 안 된다."""
    text = "<!-- DIAGRAM-LEDGER\n2×2 → 그림 | 이유\n-->\n\n# 제목\n\n본문."
    out, _ = convert_text(text, ALIASES, TITLES)
    assert "DIAGRAM-LEDGER" not in out
    assert out.lstrip().startswith("# 제목")
