"""factcheck 양방향 테스트.

GPT 호출은 테스트하지 않는다 — 기계 부분(본문 추출·프롬프트 생성·응답 파싱·리포트·
라운드 캡)만 검증한다. 최우선은 오탐 방지와 깨진 입력 방어: 팩트체커가 크래시하거나
멀쩡한 통과 항목을 노이즈로 뱉으면 사람이 무시한다.
"""

import json

import pytest

from blog_harness.factcheck import (
    MAX_ROUNDS,
    Claim,
    SpecError,
    _find_guides_dir,
    apply_main,
    build_prompt,
    build_report,
    count_rounds,
    extract_body,
    load_source_rules,
    main,
    parse_response,
)

GUIDES = str(_find_guides_dir())


# ── 본문 추출 ──────────────────────────────────────────────────────────────
DRAFT = """\
---
category: ComfyUI
tags: [Anima, 정리]
---

# 제목

## 본론

Anima는 20억 파라미터로 비교적 가볍다.

```python
params = 2_000_000_000
```

[IMG: Anima 구조도 — 인코더/디코더]

![구조도](anima.png) 위 그림처럼 동작한다.

내 RTX 4060에서는 이 설정이 안 먹었다.
"""


def test_extract_body_drops_code_and_images():
    """프런트매터·코드 블록·IMG placeholder·이미지 마크다운을 제거한다."""
    body = extract_body(DRAFT)
    assert "20억 파라미터" in body
    assert "RTX 4060" in body
    assert "params = 2_000_000_000" not in body  # 코드 블록
    assert "category: ComfyUI" not in body  # 프런트매터
    assert "[IMG:" not in body  # placeholder
    assert "anima.png" not in body  # 이미지 마크다운
    assert "위 그림처럼 동작한다" in body  # 이미지 뒤 산문은 남는다


def test_extract_body_without_frontmatter():
    """프런트매터가 없어도 본문을 그대로 통과시킨다."""
    assert extract_body("# 제목\n\n내용.") == "# 제목\n\n내용."


# ── §2.1 출처 표 파싱 (doc-parse) ──────────────────────────────────────────
def test_source_rules_parsed_from_writing_md():
    """writing.md §2.1 표를 파싱한다 (코드 상수 아님)."""
    rules = load_source_rules(GUIDES)
    assert "RFC" in rules
    assert "파라미터 수" in rules
    assert "1인칭 경험" in rules


def test_missing_source_table_raises(tmp_path):
    """§2.1 표가 없으면 SpecError."""
    (tmp_path / "writing.md").write_text("## 2. 출처\n\n표 없음", encoding="utf-8")
    load_source_rules.cache_clear()
    with pytest.raises(SpecError) as exc:
        load_source_rules(str(tmp_path))
    assert "2.1" in str(exc.value)
    load_source_rules.cache_clear()


# ── 프롬프트 (진짜 산출물) ─────────────────────────────────────────────────
def test_prompt_contains_fact02_instruction_and_categories():
    """FACT-02 지시문 + 5개 카테고리 + EXPERIENCE 예시 + §2.1 표가 프롬프트에 있다."""
    prompt = build_prompt("본문", load_source_rules(GUIDES))
    # FACT-02 — 에코 챔버 차단 문장
    assert "너 자신의 지식으로" in prompt
    assert "글 안에 근거가 제시돼 있는지만 본다" in prompt
    # FACT-01 — 5개 카테고리
    for cat in ("VERIFIED", "CONTRADICTED", "UNSOURCED", "HEDGE_NEEDED", "EXPERIENCE"):
        assert cat in prompt
    # EXPERIENCE 예시 (false-positive 가드)
    assert "RTX 4060" in prompt
    # §2.1 표 유입
    assert "RFC" in prompt
    # 본문 유입
    assert "본문" in prompt


# ── 응답 파싱 (깨진 JSON 방어) ─────────────────────────────────────────────
GOOD_RESPONSE = json.dumps(
    [
        {"claim": "Anima는 20억 파라미터로 비교적 가볍다.", "verdict": "UNSOURCED",
         "reason": "본문에 출처 없음", "suggestion": "모델 카드 링크"},
        {"claim": "내 RTX 4060에서는 이 설정이 안 먹었다.", "verdict": "EXPERIENCE",
         "reason": "1인칭 환경 관찰", "suggestion": ""},
    ],
    ensure_ascii=False,
)


def test_parse_valid_response():
    """정상 JSON → Claim 목록. verdict 는 대문자 정규화."""
    claims = parse_response(GOOD_RESPONSE)
    assert len(claims) == 2
    assert claims[0].verdict == "UNSOURCED"
    assert claims[1].verdict == "EXPERIENCE"


def test_parse_tolerates_json_fence_and_preamble():
    """```json 펜스·머리말이 붙어도 첫 [ ~ 마지막 ] 만 떼어 파싱한다."""
    wrapped = "여기 결과입니다:\n```json\n" + GOOD_RESPONSE + "\n```"
    assert len(parse_response(wrapped)) == 2


def test_parse_broken_json_raises_not_crash():
    """깨진 JSON 은 SpecError (스택트레이스 크래시 금지)."""
    with pytest.raises(SpecError) as exc:
        parse_response('[{"claim": "x", "verdict": ')
    assert "JSON" in str(exc.value)


def test_parse_missing_required_key_raises():
    """claim/verdict 키가 없으면 SpecError."""
    with pytest.raises(SpecError):
        parse_response('[{"claim": "x"}]')


# ── 리포트 (정렬·통과 숨김·파일:줄) ────────────────────────────────────────
DRAFT_FOR_REPORT = "\n".join(
    ["# 제목", "", "Anima는 20억 파라미터로 비교적 가볍다.", "", "이건 확실히 틀렸다.", "", "내 RTX 4060에서는 안 먹었다."]
)
REPORT_CLAIMS = [
    Claim("내 RTX 4060에서는 안 먹었다.", "EXPERIENCE", "1인칭", ""),
    Claim("Anima는 20억 파라미터로 비교적 가볍다.", "UNSOURCED", "출처 없음", "링크"),
    Claim("이건 확실히 틀렸다.", "CONTRADICTED", "출처와 어긋남", "수정"),
]


def test_report_sorted_by_severity():
    """CONTRADICTED → UNSOURCED 순으로 출력된다 (심각도순)."""
    report, _, _ = build_report(REPORT_CLAIMS, "drafts/x.md", DRAFT_FOR_REPORT)
    assert report.index("CONTRADICTED") < report.index("UNSOURCED")


def test_report_hides_passing_verdicts():
    """EXPERIENCE·VERIFIED 는 개별 출력하지 않고 요약 카운트에만 (노이즈 방지)."""
    report, _, _ = build_report(REPORT_CLAIMS, "drafts/x.md", DRAFT_FOR_REPORT)
    # 개별 블록에 EXPERIENCE 항목이 없다
    assert "[EXPERIENCE]" not in report
    # 요약에는 카운트가 있다
    assert "EXPERIENCE 1" in report


def test_report_includes_file_line():
    """파일:줄 번호가 붙는다 (에디터 점프용)."""
    report, _, _ = build_report(REPORT_CLAIMS, "drafts/x.md", DRAFT_FOR_REPORT)
    assert "drafts/x.md:3" in report  # "Anima..." 는 3번째 줄


def test_report_exit_code():
    """SEVERITY 있으면 exit 1, 통과만 있으면 exit 0."""
    _, code_flagged, _ = build_report(REPORT_CLAIMS, "drafts/x.md", DRAFT_FOR_REPORT)
    assert code_flagged == 1
    passing_only = [Claim("내 RTX 4060에서는 안 먹었다.", "EXPERIENCE", "1인칭", "")]
    _, code_clean, _ = build_report(passing_only, "drafts/x.md", DRAFT_FOR_REPORT)
    assert code_clean == 0


def test_report_unknown_verdict_surfaced():
    """미지의 판정은 숨기지 않고 개별 출력 + flagged (사람에게 노출)."""
    claims = [Claim("뭔가", "WEIRD", "?", "")]
    report, code, _ = build_report(claims, "drafts/x.md", "뭔가")
    assert "WEIRD" in report
    assert code == 1


# ── 라운드 캡 / 교착 (FACT-03) ─────────────────────────────────────────────
def test_count_rounds():
    """로그의 '## Round N' 헤더를 센다."""
    log = "## Round 1 — 2026\n\n...\n\n## Round 2 — 2026\n\n..."
    assert count_rounds(log) == 2
    assert count_rounds("") == 0


# ── main / apply_main exit 코드 (end-to-end IO) ────────────────────────────
# _find_guides_dir/_find_repo_root 는 __file__ 기준으로 실 저장소를 찾으므로, IO 테스트는
# 두 로케이터를 tmp 저장소로 monkeypatch 한다 (실 factcheck/ 오염 방지).
def _mini_repo(tmp_path, monkeypatch):
    """writing.md §2.1 표를 가진 최소 저장소 + 로케이터 패치."""
    (tmp_path / "guides").mkdir()
    (tmp_path / "guides" / "writing.md").write_text(
        "## 2. 출처\n\n### 2.1 원칙\n\n"
        "| 대상 | 출처 필요 |\n|---|---|\n"
        "| RFC 번호, 표준 스펙 | ✅ |\n"
        "| 성능 수치, 파라미터 수 | ✅ |\n"
        "| 1인칭 경험·환경 관찰 | ❌ 불필요 |\n\n"
        "### 2.2 다음\n",
        encoding="utf-8",
    )
    (tmp_path / "factcheck").mkdir()
    monkeypatch.setattr("blog_harness.factcheck._find_guides_dir", lambda: tmp_path / "guides")
    monkeypatch.setattr("blog_harness.factcheck._find_repo_root", lambda: tmp_path)
    load_source_rules.cache_clear()
    return tmp_path


def test_apply_deadlock_past_max_rounds(tmp_path, monkeypatch):
    """로그에 MAX_ROUNDS 라운드가 있으면 다음 apply 는 교착 보고 + exit 1, append 안 함."""
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("Anima는 20억 파라미터.", encoding="utf-8")
    (repo / "factcheck" / "foo.response.json").write_text(
        json.dumps([{"claim": "Anima는 20억 파라미터.", "verdict": "UNSOURCED",
                     "reason": "r", "suggestion": "s"}], ensure_ascii=False),
        encoding="utf-8",
    )
    log = repo / "factcheck" / "foo.log.md"
    filled = "".join(f"## Round {i} — 2026\n\n...\n\n" for i in range(1, MAX_ROUNDS + 1))
    log.write_text(filled, encoding="utf-8")

    assert apply_main([str(draft)]) == 1
    # append 되지 않았다 (여전히 MAX_ROUNDS 개)
    assert count_rounds(log.read_text(encoding="utf-8")) == MAX_ROUNDS


def test_main_generates_prompt(tmp_path, monkeypatch):
    """make factcheck → prompt.txt 생성, FACT-02 문장·EXPERIENCE 포함, exit 0."""
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("Anima는 20억 파라미터로 가볍다.", encoding="utf-8")
    assert main([str(draft)]) == 0
    prompt = (repo / "factcheck" / "foo.prompt.txt").read_text(encoding="utf-8")
    assert "너 자신의 지식으로" in prompt
    assert "EXPERIENCE" in prompt


def test_apply_returns_1_on_unsourced(tmp_path, monkeypatch):
    """UNSOURCED 있는 응답 → exit 1, 로그 append."""
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("Anima는 20억 파라미터.", encoding="utf-8")
    (repo / "factcheck" / "foo.response.json").write_text(
        json.dumps([{"claim": "Anima는 20억 파라미터.", "verdict": "UNSOURCED",
                     "reason": "r", "suggestion": "s"}], ensure_ascii=False),
        encoding="utf-8",
    )
    assert apply_main([str(draft)]) == 1
    assert (repo / "factcheck" / "foo.log.md").exists()


def test_apply_returns_2_on_missing_response(tmp_path, monkeypatch):
    """응답 파일이 없으면 exit 2 (안내 출력)."""
    repo = _mini_repo(tmp_path, monkeypatch)
    draft = repo / "foo.md"
    draft.write_text("내용", encoding="utf-8")
    assert apply_main([str(draft)]) == 2
