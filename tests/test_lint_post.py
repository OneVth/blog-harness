"""lint_post 양방향 테스트.

거짓말하는 하네스는 없느니만 못하다 — false negative(놓침)와 false positive(오탐)를
모두 검증한다. 최우선은 오탐 방지: 멀쩡한 글은 조용히 통과해야 한다.
"""

from pathlib import Path

import pytest

from blog_harness.lint_post import (
    WARN,
    SpecError,
    _find_guides_dir,
    check_dead_links,
    check_dramatic_idiom,
    check_image_refs,
    check_img_placeholder,
    check_tags,
    lint_metadata,
    lint_post_text,
    load_categories,
    load_dramatic_idioms,
    load_source_tags,
    main,
    parse_frontmatter,
)

REPO = Path(__file__).resolve().parents[1]
GUIDES = str(_find_guides_dir())
VALID = load_categories(GUIDES)
SOURCES = load_source_tags(GUIDES)
IDIOMS = load_dramatic_idioms(GUIDES)


def ids(findings) -> list[str]:
    return [f.rule_id for f in findings]


def levels(findings) -> set[str]:
    return {f.level for f in findings}


def tag_ids(tags: list[str]) -> list[str]:
    return ids(check_tags(tags, VALID, SOURCES))


# 최소 정상 글: 제목·섹션·마무리·언어태그 코드블록. 대시·이미지 없음.
CLEAN_POST = """# 제목 — 부제에는 대시를 써도 된다

## 들어가며

이 글은 무언가를 설명한다. 가운뎃점(·)은 나열에 쓴다: NAC·방화벽·WAF.

## 본론

```python
print("hello")
```

## 마무리

읽는 법은 한 줄로 압축한다.
"""


# ── false positive 방지 (조용히 통과해야 함) ──────────────────────────────
def test_clean_post_lints_clean():
    """규격을 지킨 글은 본문 findings == [] 여야 한다."""
    assert lint_post_text(CLEAN_POST) == []


def test_valid_category_passes():
    """CATEGORIES 블록에 있는 카테고리는 통과."""
    assert lint_metadata("Infra", None, GUIDES) == []
    assert lint_metadata("OSS Tools", None, GUIDES) == []  # 공백 포함


def test_normal_tag_set_passes():
    """정상 3축 태그 조합은 조용히 통과."""
    assert check_tags(["Docker", "Ubuntu", "정리"], VALID, SOURCES) == []
    assert check_tags(["Firecrawl", "SelfHosting", "Docker", "정리"], VALID, SOURCES) == []


@pytest.mark.parametrize("tag", ["Redis", "Kubernetes", "macOS", "HTTPS", "Class", "Bus", "Axis"])
def test_non_plural_s_tags_pass(tag):
    """'s' 로 끝나지만 복수형이 아닌 태그는 POST-05a 를 내지 않는다 (오탐 방지 핵심)."""
    assert "POST-05a" not in tag_ids([tag])


def test_dash_in_structural_lines_passes():
    """제목·IMG 라벨·표 셀의 대시는 POST-10 대상이 아니다."""
    text = (
        "# NAT — 하나의 주소로 여럿이 쓰는 법\n\n"
        "## NAT란 — 주소와 포트를 바꿔치기하는 기술\n\n"
        "[IMG: Symmetric NAT #1 — 출발지 IP 192.168.0.10]\n\n"
        "| 값 — 설명 |\n|---|\n| a — b |\n\n"
        "## 마무리\n\n끝."
    )
    assert "POST-10" not in ids(lint_post_text(text))


def test_middle_dot_not_flagged():
    """가운뎃점(·)은 대시가 아니다 — POST-10 을 내지 않는다."""
    text = "## 본론\n\nNAC·방화벽·WAF 는 나열이다.\n\n## 마무리\n\n끝."
    assert "POST-10" not in ids(lint_post_text(text))


def test_existing_image_passes(tmp_path):
    """diagrams/ 아래 존재하는 이미지는 POST-07 통과."""
    (tmp_path / "diagrams" / "net").mkdir(parents=True)
    (tmp_path / "diagrams" / "net" / "vpn.png").write_bytes(b"x")
    text = "![VPN 개념도](vpn.png)"
    assert check_image_refs(text, repo_root=tmp_path) == []


def test_remote_image_not_existence_checked(tmp_path):
    """http(s) 원격 이미지는 존재 검사에서 제외 (링크 생존은 POST-06)."""
    text = "![alt](https://example.com/x.png)"
    assert "POST-07" not in ids(check_image_refs(text, repo_root=tmp_path))


def test_lychee_absent_skips_gracefully(monkeypatch):
    """lychee 가 없으면 POST-06 은 스킵된다 (findings 없음, skipped True)."""
    monkeypatch.setattr("blog_harness.lint_post.shutil.which", lambda _: None)
    findings, skipped = check_dead_links(["posts/"])
    assert findings == []
    assert skipped is True


# ── 카테고리 파싱 (doc-parse) ──────────────────────────────────────────────
def test_categories_parsed_from_block():
    """categories.md CATEGORIES 블록을 파싱한다 (공백 포함 이름 포함)."""
    assert "Embedded" in VALID
    assert "OS" in VALID
    assert "ComfyUI" in VALID
    assert "OSS Tools" in VALID
    assert "Language" not in VALID  # 컨테이너는 블록에 없다


def test_missing_categories_block_raises(tmp_path):
    """CATEGORIES 마커가 없으면 SpecError."""
    (tmp_path / "categories.md").write_text("no markers here", encoding="utf-8")
    load_categories.cache_clear()
    with pytest.raises(Exception) as exc:
        load_categories(str(tmp_path))
    assert "CATEGORIES" in str(exc.value)
    load_categories.cache_clear()


def test_source_tags_parsed():
    """tags.md §4 표에서 Source 태그를 파싱한다."""
    assert "CSAPP" in SOURCES
    assert "OSTEP" in SOURCES


# ── false negative 방지 (잡아야 함) ────────────────────────────────────────
def test_invalid_category_flagged():
    """CATEGORIES 블록에 없는 카테고리는 POST-01 ERROR."""
    findings = lint_metadata("NoSuchCat", None, GUIDES)
    assert "POST-01" in ids(findings)
    assert findings[0].level == "ERROR"


@pytest.mark.parametrize(
    "tags,rule",
    [
        (["회고", "정리", "Docker"], "POST-03"),  # Kind 2개
        (["삽질", "Docker"], "POST-03"),  # deprecated
        (["a", "b", "c", "d", "e", "f", "g"], "POST-02"),  # Topic 7개
        ([], "POST-02"),  # 0개
        (["a", "b", "c", "d", "e", "f", "g", "h", "i"], "POST-02"),  # 총 9개
        (["Embedded", "Docker"], "POST-04"),  # 카테고리 동명
        (["DSA", "Docker"], "POST-04"),
        (["추천", "Docker"], "POST-05b"),  # 주관적
        (["총정리", "Docker"], "POST-05b"),
        (["기억할것", "Docker"], "POST-05c"),  # 개인 분류
        (["type/생성", "Docker"], "POST-05c"),  # 경로 형식
        (["나중에", "Docker"], "POST-05c"),
    ],
)
def test_bad_tags_flagged(tags, rule):
    """각 태그 규칙이 해당 규칙 ID를 낸다."""
    assert rule in tag_ids(tags)


def test_plural_tag_warns_with_registration_hint():
    """복수형 후보는 POST-05a WARN + NOT_PLURAL 등록 경로를 안내한다."""
    findings = check_tags(["Arrays", "Docker"], VALID, SOURCES)
    p05a = [f for f in findings if f.rule_id == "POST-05a"]
    assert p05a
    assert p05a[0].level == "WARN"
    assert "Array" in p05a[0].message
    assert "NOT_PLURAL" in p05a[0].message


def test_deep_heading_warns():
    """#### 이하 섹션은 POST-08 WARN."""
    text = "# 제목\n\n## 섹션\n\n#### 너무 깊다\n\n## 마무리\n\n끝."
    findings = lint_post_text(text)
    p08 = [f for f in findings if f.rule_id == "POST-08"]
    assert p08 and p08[0].level == "WARN"


def test_missing_conclusion_warns():
    """마무리/정리 로 끝나지 않으면 POST-09 WARN."""
    text = "# 제목\n\n## 본론\n\n내용.\n\n## 설치 완료\n\n끝."
    assert "POST-09" in ids(lint_post_text(text))


def test_body_prose_dash_warns():
    """본문 산문의 대시는 POST-10 WARN."""
    text = "# 제목\n\n## 본론\n\nInline, Out of path, Proxy—이 셋 중 하나다.\n\n## 마무리\n\n끝."
    findings = lint_post_text(text)
    p10 = [f for f in findings if f.rule_id == "POST-10"]
    assert p10 and p10[0].level == "WARN"


def test_code_fence_without_lang_warns():
    """언어 태그 없는 코드펜스는 POST-11 WARN."""
    text = "# 제목\n\n## 본론\n\n```\nprint(1)\n```\n\n## 마무리\n\n끝."
    assert "POST-11" in ids(lint_post_text(text))


def test_missing_image_flagged(tmp_path):
    """diagrams/ 에 없는 이미지 참조는 POST-07 ERROR."""
    (tmp_path / "diagrams").mkdir()
    findings = check_image_refs("![alt](gone.png)", repo_root=tmp_path)
    assert "POST-07" in ids(findings)
    assert [f for f in findings if f.rule_id == "POST-07"][0].level == "ERROR"


def test_empty_alt_warns(tmp_path):
    """alt 텍스트가 비면 POST-07 WARN."""
    (tmp_path / "diagrams").mkdir()
    (tmp_path / "diagrams" / "x.png").write_bytes(b"x")
    findings = check_image_refs("![](x.png)", repo_root=tmp_path)
    p07 = [f for f in findings if f.rule_id == "POST-07"]
    assert p07 and p07[0].level == "WARN"


# ── main() exit 코드 ───────────────────────────────────────────────────────
def test_main_clean_returns_0(tmp_path):
    """규격 글 + 정상 메타데이터면 exit 0."""
    post = tmp_path / "ok.md"
    post.write_text(CLEAN_POST, encoding="utf-8")
    assert main([str(post), "--category", "Infra", "--tags", "Docker,정리", "--no-links"]) == 0


def test_main_error_returns_1(tmp_path):
    """ERROR(잘못된 카테고리)면 exit 1."""
    post = tmp_path / "ok.md"
    post.write_text(CLEAN_POST, encoding="utf-8")
    assert main([str(post), "--category", "NoSuch", "--no-links"]) == 1


def test_main_strict_promotes_warn(tmp_path):
    """WARN 만 있을 때 기본은 0, --strict 면 1."""
    post = tmp_path / "warn.md"
    post.write_text("# 제목\n\n## 본론\n\n내용.\n\n## 설치 완료\n\n끝.", encoding="utf-8")
    assert main([str(post), "--no-links"]) == 0
    assert main([str(post), "--strict", "--no-links"]) == 1


# ── POST-12: 극적 수사 어휘 ────────────────────────────────────────────────
def test_dramatic_idiom_warns():
    """본문 산문의 극적 관용구는 POST-12 WARN."""
    text = "# 제목\n\n## 들어가며\n\n이 문제의 열쇠는 상태를 못 박는 것이다.\n\n## 마무리\n\n끝."
    findings = lint_post_text(text)
    assert "POST-12" in ids(findings)
    assert WARN in {f.level for f in findings if f.rule_id == "POST-12"}


def test_dramatic_idiom_skips_structural_and_code():
    """제목·IMG·표·코드펜스 안의 어휘는 POST-12 대상이 아니다 (오탐 방지)."""
    text = (
        "# 심장이다 라는 부제\n\n[IMG: x — 열쇠는 여기]\n\n"
        "| 열쇠는 | 지배한다 |\n|---|---|\n\n```text\n못 박는다\n```\n\n## 마무리\n\n끝."
    )
    assert "POST-12" not in ids(check_dramatic_idiom(text, IDIOMS))


def test_dramatic_idioms_parsed_from_block():
    """writing.md §4.3 DRAMATIC_IDIOMS 블록이 파싱된다."""
    assert "못 박" in IDIOMS
    assert "열쇠는" in IDIOMS


def test_missing_dramatic_block_raises(tmp_path):
    (tmp_path / "writing.md").write_text("no markers here", encoding="utf-8")
    load_dramatic_idioms.cache_clear()
    with pytest.raises(SpecError):
        load_dramatic_idioms(str(tmp_path))
    load_dramatic_idioms.cache_clear()


# ── frontmatter: 메타데이터의 집 ────────────────────────────────────────────
def test_frontmatter_parsed():
    text = "---\ncategory: DSA\ntags: [Array, 배열, 정리]\n---\n\n# 제목\n\n본문."
    cat, tags, body = parse_frontmatter(text)
    assert cat == "DSA"
    assert tags == ["Array", "배열", "정리"]
    assert body.startswith("\n# 제목")


def test_frontmatter_absent_returns_original():
    text = "# 제목\n\n본문."
    cat, tags, body = parse_frontmatter(text)
    assert (cat, tags, body) == (None, None, text)


def test_main_enforces_frontmatter_category(tmp_path):
    """CLI 인자 없이도 frontmatter 의 잘못된 카테고리를 POST-01 ERROR 로 잡는다."""
    post = tmp_path / "bad.md"
    post.write_text(
        "---\ncategory: NoSuch\ntags: [Docker]\n---\n\n" + CLEAN_POST, encoding="utf-8"
    )
    assert main([str(post), "--no-links"]) == 1


def test_main_no_metadata_notice_not_failure(tmp_path, capsys):
    """frontmatter 도 인자도 없으면 조용히 넘기지 않고 알리되, 실패는 아니다."""
    post = tmp_path / "nometa.md"
    post.write_text(CLEAN_POST, encoding="utf-8")
    assert main([str(post), "--no-links"]) == 0
    assert "미검사" in capsys.readouterr().out


# ── POST-13: [IMG:] 자작 다이어그램 파일 참조 ──────────────────────────────
def _mk_diagram(tmp_path, rel):
    p = tmp_path / "diagrams" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def test_img_placeholder_existing_passes(tmp_path):
    _mk_diagram(tmp_path, "dsa/dp_fib_tree.svg")
    text = "[IMG: dp_fib_tree — fib(5) 재귀 트리]"
    assert check_img_placeholder(text, repo_root=tmp_path) == []


def test_img_placeholder_gif_with_annotation_passes(tmp_path):
    _mk_diagram(tmp_path, "dsa/dp_longest_path.gif")
    text = "[IMG: dp_longest_path (애니메이션) — 최장 경로 움짤]"
    assert check_img_placeholder(text, repo_root=tmp_path) == []


def test_img_placeholder_drift_warns(tmp_path):
    """파일명 꼴인데 diagrams/ 에 없으면 WARN (이번 세션에 낸 dsa_ prefix 버그)."""
    _mk_diagram(tmp_path, "dsa/dp_fib_tree.svg")
    findings = check_img_placeholder("[IMG: dsa_dp_fib_tree — 오타]", repo_root=tmp_path)
    assert "POST-13" in ids(findings)
    assert WARN in {f.level for f in findings}


@pytest.mark.parametrize("text", ["[IMG: 설치 화면 스크린샷]", "[IMG: Symmetric NAT #1 — 출발지 IP]"])
def test_img_placeholder_prose_skipped(tmp_path, text):
    """산문 설명형(첫 토큰이 파일명 꼴 아님)은 검사 대상이 아니다."""
    (tmp_path / "diagrams").mkdir()
    assert check_img_placeholder(text, repo_root=tmp_path) == []
