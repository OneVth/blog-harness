# blog-harness

*[Read this in English](README.md)*

이 저장소는 블로그가 아니라 "글을 만드는 기계"다.

글 본문은 여기 살지 않는다. Obsidian(아카이브)과 Tistory(발행본)에 산다. 여기
사는 건 린터·변환기·팩트체커다.

## 왜 만들었나

글을 어떻게 쓰고, 다이어그램을 어떻게 그리고, 태그와 카테고리를 어떻게 붙일지
적어둔 설계 문서를 다섯 개 갖고 있었다. 안 지켜졌다. 문서가 틀려서가 아니라
강제력이 없어서다. 가이드에 "이렇게 해주세요" 라고 써도 무시된다.

Fowler·Böckeler 의 "harness engineering" 은 하네스를 2×2 로 본다 — 가이드,
기계 검증, LLM 판정, 그리고 사람이 루프에 있다. 내 상태는 좌상단(가이드) 한 칸만
차 있었다. 우측 두 칸(기계 검증·LLM 판정)은 비어 있었고, 그 자리를 사람이 혼자
메우고 있었다. 그건 확장되지도, 버티지도 못한다.

그래서 규칙은 하나다. **기계로 검증할 수 있는 규칙은 전부 코드로 옮긴다.**
에이전트가 실수하면 프롬프트를 고치지 말고, 그 실수가 구조적으로 재발할 수 없게
시스템을 바꾼다.

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
     └→ make build → posts/<slug>.md (callout → HTML)
     ↓ make thumbnail-prompt
     ↓ 사람: GPT에 붙여넣기       ← 게이트 ③
     ↓ make thumbnail-check + 블라인드 테스트
     ↓ 사람: Tistory 발행         ← 게이트 ④
```

사람 게이트는 의도한 것이다. 기계는 기계로 검사할 수 있는 것만 검사하고, 사람은
사람만 판단할 수 있는 걸 판단한다 (다이어그램이 의미를 전달하는가? 썸네일이 의도한
개념으로 읽히는가?).

## 규칙 계약

`guides/RULES.md` 가 린터의 계약서다. 두 원칙이 지배한다.

- **여기 있는 것만 코드가 된다. 여기 없는 것은 검사하지 않는다.**
- **false positive 금지.** 멀쩡한 것을 잡으면 사람이 린터를 무시하게 되고, 그
  순간 하네스는 죽는다. 애매하면 등급을 내린다 — ERROR → WARN → INFO.

규칙은 ID·수준·조건·출처와 함께 정의된다. 린터 에러가 규칙 ID 를 출력하고, 그 ID
로 규칙을 정의한 문서를 찾아간다. 이 README 에 규칙 개수를 일부러 쓰지 않았다 —
개수는 오직 한 곳, `RULES.md` 에만 살고 세는 건 기계가 한다 (아래 "명세는 한
곳에만" 참고).

### 검사하지 않는 것

계약서는 하네스가 **검사하지 않는** 것들의 목록으로 끝난다. 기계로 못 잡기
때문이다.

- 다이어그램이 실제로 의미를 전달하는가 — 사람이 본다 (게이트 ②).
- 썸네일 오브젝트 선정 — 초안을 읽어야 알 수 있어서 Claude 가 판단한다. 룩업
  테이블로는 안 된다.
- 썸네일이 의도한 개념으로 읽히는가 — 블라인드 테스트가 판정한다.
- 톤 판단(정의 직술, 1인칭, 절차 안내) — 의미 판단이 필요하다.
- 한글 글의 "AI 티" — `im-not-ai` 가 잡는다.
- 강의 내 실습 주제 태그 — 문맥 의존. 실습 주제인지 도메인 개념인지 기계는
  모른다.

이 목록이 중요하다. 린터가 만능인 척하면 사람이 검수를 안 하게 된다.

## 명세는 한 곳에만

명세는 딱 한 곳에만 존재해야 한다. 카테고리 목록과 썸네일 색 매핑은 **문서의 기계
판독 블록을 파싱한다.** 린터에 상수로 박지 않는다.

```
<!-- CATEGORIES:BEGIN -->
Embedded
...
<!-- CATEGORIES:END -->
```

이유: 자라는 목록을 코드에 박으면 반드시 어긋난다. 실제로 그랬다 — `OSS Tools`
카테고리가 실재하는데 문서에는 없었다. 목록을 박지 말고 문서를 파싱한다.

## 실측이 규칙을 뒤집은 사례

이 기계를 만들며 가장 배운 지점은, 실측이 설계 문서를 뒤집는 걸 지켜본 것이다.
아래는 전부 문서만 읽었으면 못 잡았다.

| 문서가 말한 것 | 실제 |
|---|---|
| viewBox 상한 720 | 900 (개발자 도구로 확인) |
| callout 에 백틱 금지 | 변환기가 `<code>` 로 바꾼다 — 문제없음 (렌더 테스트) |
| — | LaTeX 보호 필요 (`$a*b*c$` 가 `$a <em>b</em> c$` 로 깨졌다) |
| 본문 대시 금지 | 구조적 구분자는 허용 (77회 중 11회만 실제 위반) |
| 정의 직술에 1인칭 금지 | 판단 주체만 금지. 예시 참여자는 오히려 좋다 |
| 태그 복수형 = ERROR | WARN (Redis·HTTPS·macOS 오탐) |

## 재사용한 것

이미 세상에 있는 바퀴는 다시 만들지 않았다.

| 도구 | 역할 |
|---|---|
| [lychee](https://github.com/lycheeverse/lychee) | 죽은 링크 검사 |
| [im-not-ai](https://github.com/epoko77-ai/im-not-ai) | 한글 AI 티 제거 |
| ce-compound | 학습 축적 (Compound Engineering 플러그인에서 fork) |

자작한 건 세상에 없는 도메인 규칙뿐이다 — SVG 좌표 검산, Obsidian → Tistory
callout 변환, 4축 태그 컨벤션.

## 상태 — 정직하게

Phase 0~6 구현 완료 — callout → HTML `make build` 스텝을 포함한다. **아직 실제
글로 파이프라인을 돌려본 적이 없다.** 실제 글에서 깨지는 지점이 나오면, 그게
ce-compound 의 두 번째 Learning 이 된다.

## 라이선스

MIT — [LICENSE](LICENSE) 참고.

벤더링한 `ce-compound` 스킬은 Compound Engineering 플러그인(역시 MIT)의 fork 다.
출처와 수정 내역은
[.claude/skills/ce-compound/THIRD-PARTY-NOTICES.md](.claude/skills/ce-compound/THIRD-PARTY-NOTICES.md)
에 있다.

## 참고 — 하네스 엔지니어링

이 프로젝트는 하네스 엔지니어링을 **비-코딩** 도메인에 적용한 것이다.
Superpowers·Compound Engineering·Ouroboros·grill-me-codex 를 봤지만 전부 코딩
하네스였고, 그것들이 딛고 선 척추 — 컴파일러·린터·테스트 — 가 블로그엔 없다. 그
척추를 여기서는 손으로 세워야 했다.

- Martin Fowler / Birgitta Böckeler, "Harness Engineering" —
  <https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html>
- Chad Fowler, "Relocating Rigor" —
  <https://www.honeycomb.io/blog/production-is-where-the-rigor-goes>
