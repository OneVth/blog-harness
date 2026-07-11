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
| `docs/solutions/` | 트러블슈팅 기록 |
