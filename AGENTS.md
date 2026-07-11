# blog-harness

**이 저장소는 블로그가 아니라 "글을 만드는 기계"다.**

글 본문은 여기 살지 않는다 — Obsidian(아카이브)과 Tistory(발행본)에 산다.
여기 사는 것은 **린터·변환기·팩트체커**다. 설계 문서는 강제력이 없어 지켜지지
않는다. 그래서 기계로 검증 가능한 규칙을 전부 코드로 옮긴다.

## 원칙

**에이전트가 실수하면 프롬프트를 고치지 말고, 그 실수가 구조적으로 재발할 수
없도록 시스템을 바꾼다.**

프롬프트에 "이렇게 해주세요"라고 쓰면 무시된다. 규칙은 코드가 되어야 강제된다.

## 계약서

`guides/RULES.md` 가 **린터의 계약서**다. 규칙 ID(SVG-01, POST-01, CONV-01 …)와
수준(ERROR/WARN/INFO)·조건·출처가 여기 정의돼 있다.

- 여기 있는 것만 코드가 된다
- 여기 없는 것은 검사하지 않는다 (마지막 섹션 "검사하지 않는 것" 참고)
- **코드에 규칙을 상수로 박지 않는다. 문서를 파싱한다.**

## 파이프라인

```
drafts/<slug>.md
     ↓ make lint-svg      SVG 규격
     ↓ 사람: 다이어그램 검수      ← 게이트 ②
     ↓ make check         링크·태그·카테고리
     ↓ make factcheck     GPT 크로스 검증 (출처 없는 주장)
     ↓ im-not-ai          AI 티 제거 (외부 도구)
★ 최종 파일 확정
     ├→ Obsidian 아카이브 (callout 문법 그대로)
     └→ make build → posts/<cat>/<slug>.md (callout → HTML)
     ↓ make thumbnail-prompt
     ↓ 사람: GPT에 붙여넣기       ← 게이트 ③
     ↓ make thumbnail-check + 블라인드 테스트
     ↓ 사람: Tistory 발행         ← 게이트 ④
```

## 썸네일 — 누가 무엇을 정하나

상세 명세는 `guides/thumbnails.md` (§2.4 오브젝트 선정, §8.1 블라인드 테스트, §10 역할
분리)에 산다. 재진술하지 않는다. 핵심만:

- **하네스가 박는다.** `make thumbnail-prompt POST=... CATEGORY=...` 가 스타일·색·규격·
  개수·텍스트·금지목록을 결정론적으로 박은 `thumbnails/<slug>.prompt.txt` 뼈대를 만든다.
  오브젝트 자리는 `{{OBJECT}}` 로 비워둔다.
- **Claude가 고른다.** 실행 시점에 이미 초안을 읽고 있다. 개념 하나를 오브젝트 하나로
  압축해 `{{OBJECT}}` 를 채우고, 파일 맨 위 `# 개념 / # 오브젝트 / # 근거` 헤더에 판단을
  남긴다 (§2.4 절차). GPT 에게 선정을 맡기지 않는다 — 판단자 겸 생성자가 되면 "매번
  다르게 해석한다" 가 재발한다. (RULES.md "검사하지 않는 것" 에도 명시: 오브젝트 선정은
  기계 검사 대상이 아니다.)
- **GPT가 그린다.** 사람이 프롬프트를 GPT 에 붙여넣는다 (게이트 ③).
- **다른 세션의 Claude가 검증한다 (블라인드).** `make thumbnail-check THUMB=...` 가 규격을
  검사하고 `thumbnails/<slug>.150.png` 를 만든다. 그 150px 이미지 **하나만** 판정 세션에
  던진다 — **제목·카테고리·생성 프롬프트를 주지 않는다.** 정답을 주면 사후 합리화가
  일어난다. 질문: *"무슨 기술 개념인가? 한 단어. 게임 아이템 아이콘 vs 기술 개념
  아이콘?"* 의도한 개념과 맞으면 PASS, "게임 아이템"·"모르겠다" 면 REDESIGN. **재설계는
  프롬프트를 고치는 게 아니라 오브젝트 판단을 다시 하는 것이다** (§8.1). 만든 쪽(GPT)이
  채점하면 에코 챔버다.

## guides/ 읽는 법

**온디맨드로 읽는다. 전부 읽지 말 것.** 지금 하는 작업에 해당하는 규칙 ID의
출처 문서만 연다.

| 파일 | 무엇 |
|---|---|
| `RULES.md` | 린터의 계약서 (31개 규칙) — **먼저 본다** |
| `writing.md` | 글쓰기 규칙 (톤·출처·구조). **여기 산다. 재진술 금지** |
| `categories.md` · `tags.md` | 발행글 분류 |
| `callouts.md` | Obsidian → HTML 변환 계약 |
| `thumbnails.md` | 썸네일 규격 |
| `diagram-system.md` · `diagram-patterns/` | SVG 다이어그램 |

## 디렉토리

| 경로 | 용도 |
|---|---|
| `src/blog_harness/` | 하네스 코드 |
| `drafts/` | 작업 중 초안. vault를 오염시키지 않는다 |
| `diagrams/` | SVG 소스. PNG는 여기서 생성되는 산출물 (gitignore) |
| `thumbnails/` | GPT가 만든 썸네일 소스 (PNG 예외로 추적) |
| `posts/` | 변환된 발행본 (`<cat>/<slug>.md`) |
| `factcheck/` | 팩트체크 로그 |
| `docs/solutions/` | 문서화된 해결 기록 (버그·툴링 결정·워크플로·규칙) — 카테고리별 디렉토리 + YAML frontmatter(`module`·`tags`·`problem_type`)로 검색. 문서화된 영역에서 구현·디버깅·결정 시 참고. `ce-compound` 스킬이 씀 |
