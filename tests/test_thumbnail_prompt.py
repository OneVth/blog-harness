"""thumbnail_prompt 테스트.

GPT 호출은 테스트하지 않는다 — 기계 부분(색 파싱·프롬프트 조립·오브젝트 자리·IO)만
검증한다. 핵심: 뼈대는 오브젝트만 비우고 나머지(스타일·색·규격·금지)를 결정론적으로
박는가, --object 를 주면 하네스가 채우는가.
"""

import pytest

from blog_harness.thumbnail_prompt import (
    SpecError,
    _find_guides_dir,
    build_prompt,
    load_category_colors,
    main,
)

GUIDES = str(_find_guides_dir())

_COLOR_BLOCK = (
    "### 5.1 색\n\n"
    "<!-- THUMBNAIL_COLORS:BEGIN -->\n"
    "| 카테고리 | HEX | 톤 |\n|---|---|---|\n"
    "| Infra | `#9FB4CC` | 슬레이트 블루 |\n"
    "| OSS Tools | `#D99A8A` | 더스티 코랄 |\n"
    "<!-- THUMBNAIL_COLORS:END -->\n"
)


# ── 색 파싱 ────────────────────────────────────────────────────────────────
def test_load_colors_from_real_guides():
    """실 guides/thumbnails.md 를 파싱해 알려진 카테고리 색을 얻는다."""
    colors = load_category_colors(GUIDES)
    assert colors["Infra"] == "#9FB4CC"
    assert "OSS Tools" in colors  # 공백 포함 카테고리도 읽힌다


def test_load_colors_skips_header_and_separator(tmp_path):
    """헤더·구분선 행은 HEX 코드스팬이 없어 걸러진다."""
    (tmp_path / "thumbnails.md").write_text(_COLOR_BLOCK, encoding="utf-8")
    load_category_colors.cache_clear()
    colors = load_category_colors(str(tmp_path))
    assert colors == {"Infra": "#9FB4CC", "OSS Tools": "#D99A8A"}
    load_category_colors.cache_clear()


def test_missing_block_raises(tmp_path):
    """THUMBNAIL_COLORS 블록이 없으면 SpecError."""
    (tmp_path / "thumbnails.md").write_text("## 5. 배경\n\n블록 없음", encoding="utf-8")
    load_category_colors.cache_clear()
    with pytest.raises(SpecError):
        load_category_colors(str(tmp_path))
    load_category_colors.cache_clear()


# ── 프롬프트 조립 ──────────────────────────────────────────────────────────
def test_skeleton_leaves_object_and_bakes_rules():
    """오브젝트 자리는 비우고 스타일·색·규격·금지는 결정론적으로 박는다."""
    p = build_prompt("#9FB4CC", "Infra")
    assert "{{OBJECT}}" in p
    assert "{{CONCEPT}}" in p
    assert "#9FB4CC" in p
    assert "Infra" in p
    assert "Pixel Art" in p  # §4 스타일
    assert "사이버펑크" in p  # §4 금지
    assert "딱 이 오브젝트 1개만 그린다" in p
    assert "1024×1024" in p  # §3 캔버스


def test_baked_object_fills_placeholder_and_header():
    """--object/--concept/--rationale 를 주면 하네스가 박고 placeholder 는 사라진다."""
    p = build_prompt(
        "#9FB4CC",
        "Infra",
        object_text="격리된 블록들이 하나의 커널 위에",
        concept="컨테이너 격리",
        rationale="VM 없이 커널 직결",
    )
    assert "{{OBJECT}}" not in p
    assert "격리된 블록들이 하나의 커널 위에" in p
    assert "# 개념: 컨테이너 격리" in p
    assert "# 근거: VM 없이 커널 직결" in p


# ── IO (로케이터 monkeypatch — 실 thumbnails/ 오염 방지) ────────────────────
def _mini_repo(tmp_path, monkeypatch):
    (tmp_path / "guides").mkdir()
    (tmp_path / "guides" / "thumbnails.md").write_text(_COLOR_BLOCK, encoding="utf-8")
    (tmp_path / "thumbnails").mkdir()
    monkeypatch.setattr(
        "blog_harness.thumbnail_prompt._find_guides_dir", lambda: tmp_path / "guides"
    )
    monkeypatch.setattr(
        "blog_harness.thumbnail_prompt._find_repo_root", lambda: tmp_path
    )
    load_category_colors.cache_clear()
    return tmp_path


def test_main_writes_skeleton(tmp_path, monkeypatch):
    """make thumbnail-prompt → thumbnails/<slug>.prompt.txt 뼈대 생성, exit 0."""
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("# Docker Engine 설치\n\n본문", encoding="utf-8")
    assert main([str(draft), "--category", "Infra"]) == 0
    out = (repo / "thumbnails" / "foo.prompt.txt").read_text(encoding="utf-8")
    assert "{{OBJECT}}" in out
    assert "#9FB4CC" in out
    load_category_colors.cache_clear()


def test_main_bakes_object_when_given(tmp_path, monkeypatch):
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("본문", encoding="utf-8")
    code = main([str(draft), "--category", "Infra", "--object", "격리된 블록"])
    assert code == 0
    out = (repo / "thumbnails" / "foo.prompt.txt").read_text(encoding="utf-8")
    assert "{{OBJECT}}" not in out
    assert "격리된 블록" in out
    load_category_colors.cache_clear()


def test_main_missing_draft_returns_2(tmp_path, monkeypatch):
    _mini_repo(tmp_path, monkeypatch)
    assert main([str(tmp_path / "nope.md"), "--category", "Infra"]) == 2
    load_category_colors.cache_clear()


def test_main_unknown_category_returns_2(tmp_path, monkeypatch):
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("본문", encoding="utf-8")
    assert main([str(draft), "--category", "Nonexistent"]) == 2
    load_category_colors.cache_clear()
