---
title: CE 플러그인 ce-compound 스킬을 저장소 안으로 fork 이식
date: 2026-07-12
category: tooling-decisions
module: harness-skills
problem_type: tooling_decision
component: tooling
severity: low
applies_when:
  - "외부 스킬·도구를 이 하네스로 가져올 때"
  - "upstream 플러그인의 일부만 떼어내 수정해 쓸 때"
  - "학습·트러블슈팅 축적 도구를 도입할 때"
tags:
  - vendoring
  - skills
  - compound-engineering
  - docs-solutions
  - fork
  - discoverability
---

# CE 플러그인 ce-compound 스킬을 저장소 안으로 fork 이식

## Context

blog-harness 는 이미 학습을 **수동으로** 축적하고 있었다. 다이어그램 문서의 버전
이력이 그 증거다 — "동심원 배치 폐기 — 간선이 사방으로 뻗어 가독성 나쁨", "소켓
구분선 1px 침범 검산". 이건 정확히 *문제 → 실패한 시도 → 근본 원인 → 해결 → 재발
방지* 구조이고, CE 플러그인(`github.com/EveryInc/compound-engineering-plugin`,
MIT)의 `ce-compound` 스킬 bug-track 섹션과 1:1로 대응한다.

이 수동 축적을 구조화하되, 산출물이 `docs/solutions/` 에 **쌓이기만 하고 아무도 안
읽는 무덤**이 되지 않게 하는 도구가 필요했다. `ce-compound` **한 스킬만** 가져오기로
했다 (`ce-compound-refresh`·`ce-sessions`·`/ce-plan` 등 나머지 CE 스킬은 제외).

## Guidance

**1. `~/.claude/skills/` 가 아니라 저장소 안(`.claude/skills/ce-compound/`)에 둔다.**
SKILL.md 를 수정하는 fork 이기 때문이다. 판단 근거 네 가지:
- fork 는 버전 관리되는 곳에 살아야 무엇을 왜 고쳤는지 이력이 남는다.
- 축적 대상인 `docs/solutions/` 가 이 저장소 안에 산다. 다른 프로젝트가 이 학습을
  읽을 이유가 없다.
- 하네스는 저장소 안에서 자기완결적이어야 한다. clone 한 사람에게 안 보이는 스킬은
  존재하지 않는 것과 같다.
- `~/.claude/skills/` 는 소유자 없는 규칙이 사는 곳이다 — 이 저장소의 전제("명세는
  버전 관리되는 한 곳에")와 충돌한다.

**2. fork 이력은 `.orig` 백업이 아니라 커밋 메시지로 남긴다.** 로컬 커밋 `5ef675c` 에
출처(`EveryInc/compound-engineering-plugin@7f86be9d`, upstream main HEAD — 이
저장소가 아니라 upstream 의 SHA다)와 "무엇을 제거/유지했고 왜"를 박았다. `git log`
가 fork 이력이 되고, upstream 갱신 시 그 SHA 기준으로 diff 를 뜰 수 있다.

**3. dangling 참조를 전부 떼어낸다 — 전부 산문이라 기능은 안 깨진다.** 안 가져온
스킬/커맨드를 가리키는 참조는 실행 경로가 아니라 권고·redirect·비유·"invoke 하지
마라" 주석뿐이었다. 제거 목록:
- `ce-compound-refresh` (SKILL.md 안에만 21회). 이걸 호출하는 게 유일 존재 이유인
  **Phase 2.5 (Selective Refresh Check)** 통째 포함.
- `/ce-plan` (Related Commands), `ce-code-review` (scratch 비유), `ce-simplify-code`
  (Phase 3 "do not invoke" + When to Invoke 포인터).
- `/research`, `ce-sessions`·`code-simplicity-reviewer` "deleted skill" 주석.

**4. Phase 2.5 는 삭제가 아니라 "Stale-Doc Note (manual review)" 로 대체한다.**
자동 refresh 스킬은 없앴지만, Related Docs Finder 가 잡는 "이 학습이 옛 문서를
낡게 만들었을 수 있다"는 **신호 자체는 가치가 있다**. 그래서 죽은 자동화(호출 +
`/ce-compound-refresh <scope>` 예시 4개)만 걷어내고, 후보를 출력에 남겨 사람이
검토하게 하는 3줄 노트로 바꿨다.

**5. Discoverability Check 는 반드시 살린다.** 이게 이식의 핵심이다. `docs/solutions/`
(와 존재 시 `CONCEPTS.md`)를 AGENTS.md/CLAUDE.md 에 등록해, 에이전트가 작업 전
이 저장소를 검색하도록 만든다. refresh·커맨드 의존이 전혀 없어 정리 후에도 온전하다.
**이게 없으면 학습이 쌓이기만 하고 아무도 안 읽는 무덤이 된다.**

**6. `mode:lightweight` 명시 토큰을 추가한다.** 원본은 `mode:headless` 만 토큰이고
Full/Lightweight 는 컨텍스트 압력으로 자동 선택돼서, "첫 실행은 싼 Lightweight 로"를
결정론적으로 강제할 수단이 없었다. frontmatter·Mode Detection·Execution Strategy
세 곳에 오버라이드를 박았다.

> **주의 — Lightweight 는 AGENTS.md 를 편집하지 않는다 (팁만 출력).** Discoverability
> Check 의 실제 instruction-file 편집은 interactive/Full 실행 몫이다. 이 문서를 만든
> 첫 실행에서 `docs/solutions/` 를 AGENTS.md 에 등록한 것은 순수 Lightweight 가
> 아니라 interactive 형태로 별도 수행한 결과다. 다음에 Lightweight 를 쓸 땐 등록이
> 자동으로 안 일어난다는 걸 알고 써라.

## Why This Matters

이 저장소의 원칙은 "규칙은 코드가 되어야 강제된다"이고, 따름 원칙은 "에이전트에게
안 보이는 지식은 존재하지 않는다"이다. `ce-compound` 는 첫 번째를(학습을 구조화된
검사 가능 산출물로), Discoverability Check 는 두 번째를(그 산출물을 에이전트가 찾게)
충족한다. Discoverability Check 를 떨어뜨렸다면 잘 돌아가는 축적기를 얻되 아무도 안
읽는 무덤을 함께 얻었을 것이다 — 도구의 목적이 정확히 무효화된다.

fork 를 저장소 안에 두고 출처를 커밋에 박는 선택도 같은 원칙이다: clone 한 사람이
스킬과 그 수정 이력을 함께 본다. 하네스가 자기완결적이 된다.

## When to Apply

외부 스킬·도구를 이 하네스로 가져올 때 이 패턴을 따른다:
- 저장소 안으로 fork (수정한다면 `~/.claude/` 전역이 아니라 `.claude/` 로컬).
- 안 가져오는 부분을 가리키는 dangling 교차참조를 전부 제거. 단, 그게 나르던
  **신호**가 가치 있으면 자동화만 걷어내고 신호는 수동 노트로 보존.
- 도구를 발견·등록하는 메커니즘(여기선 Discoverability Check)은 반드시 보존.
- 출처(upstream SHA)와 제거/유지 근거를 커밋 메시지에 박는다. `.orig` 백업 금지.

## Examples

제거가 안전했던 근거 — dangling 참조는 전부 실행 경로가 아닌 산문이었다:

```
# Phase 2.5 (제거 전): ce-compound-refresh 호출이 존재 이유
- /ce-compound-refresh plugin-versioning-requirements
- /ce-compound-refresh payments
...
# (제거 후): Stale-Doc Note — 후보만 출력에 남기고 사람이 판단
```

AGENTS.md 디렉토리 표의 `docs/solutions/` 한 줄이 "트러블슈팅 기록"뿐이라
구조·검색법·언제 볼지가 없었다 → Discoverability Check 가 이 갭을 잡는다.

## Related

- `guides/RULES.md` "검사하지 않는 것" — 기계 검사 대상과 사람 판단 대상의 경계.
- `.claude/skills/ce-compound/SKILL.md` — 이식·정리된 스킬 본체.
- 커밋 `5ef675c` — 이 이식의 fork 이력과 출처 SHA.
