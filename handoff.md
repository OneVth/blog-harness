# blog-harness — Claude Code 위임 프롬프트

각 Phase를 **별도 세션**으로 실행한다. 한 세션에 몰아넣지 말 것 — 컨텍스트가 40%를
넘으면 지시 준수 능력이 급락한다. 상태는 git과 파일에 산다.

**Phase N을 시작하기 전에 Phase N-1이 커밋되어 있어야 한다.**

---

## 핵심 원칙 — 프롬프트가 규칙을 말하지 않는다

`guides/RULES.md`가 **린터의 계약서**다. 31개 규칙이 ID·수준·조건·출처와 함께 정의돼 있다.

**프롬프트는 규칙을 재진술하지 않는다.** 재진술하면 두 곳이 어긋나고, 그게 정확히
이 프로젝트가 없애려는 문제다 (문서는 720이라 하는데 실제는 900이었던 것처럼).

프롬프트는 이렇게만 말한다:

```
guides/RULES.md 의 SVG-01 ~ SVG-09 를 구현하라.
```

---

## 사전 준비 (사람이 직접)

```bash
mkdir -p ~/workspace/projects/blog-harness
cd ~/workspace/projects/blog-harness
git init
mkdir -p guides/diagram-patterns
```

**`guides/` 전체를 넣는다** (이 세션에서 만든 19개 파일):

```
guides/
├── RULES.md              ★ 린터의 계약서. 31개 규칙
├── categories.md         13개 카테고리 + 기계 판독 블록
├── tags.md               3축 모델
├── callouts.md           8종 · alias · 변환 계약
├── thumbnails.md         13색 매핑 + 기계 판독 블록
├── writing.md            톤 3종 · 출처 · 구조
├── diagram-system.md     지도
└── diagram-patterns/     12개 (온디맨드)
```

```bash
git add guides/ && git commit -m "guides: 명세 확정"
```

---

# Phase 0 — 저장소 골격

```
Tistory 기술 블로그의 발행 하네스를 만든다.

이 저장소는 "블로그"가 아니라 "글을 만드는 기계"다. 글 자체는 Obsidian(아카이브)과
Tistory(발행본)에 산다. 여기 사는 것은 린터·변환기·팩트체커다.

## 왜 만드는가

나는 설계 문서를 갖고 있었지만 지켜지지 않았다. 강제력이 없었기 때문이다.
문서에 "이렇게 해주세요"라고 써도 무시된다. 그래서 기계로 검증 가능한 규칙을
전부 코드로 옮긴다.

## 먼저 읽어라

`guides/RULES.md` — **이것이 이 프로젝트의 계약서다.**

  - 여기 있는 것만 코드가 된다
  - 여기 없는 것은 검사하지 않는다
  - 마지막 섹션 "검사하지 않는 것"을 반드시 읽어라

## Phase 0에서 할 일

Python 3.12+ / uv 기반 골격.

1. `pyproject.toml`
   - name: blog-harness, requires-python >=3.12
   - **런타임 의존성 비움.** 필요할 때만 추가한다.
     하네스는 rippable해야 한다 — 모델이 좋아지면 절반은 버리게 된다
   - dev: pytest, ruff
   - hatchling, src 레이아웃
   - `[project.scripts]` 는 도구가 생길 때마다 추가

2. 디렉토리
   ```
   src/blog_harness/__init__.py
   drafts/.gitkeep          # 작업 중인 초안. vault를 오염시키지 않는다
   diagrams/_template/
   thumbnails/.gitkeep
   posts/.gitkeep
   factcheck/.gitkeep
   docs/solutions/.gitkeep
   tests/
   ```

3. `.gitignore`
   - `*.png` — **PNG는 SVG에서 생성되는 산출물이다**
   - **예외**: `thumbnails/*.png` 는 GPT가 만든 소스다. negate 처리
   - `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`

4. `Makefile` — 지금은 setup/test/lint만. Phase마다 타겟 추가

5. `AGENTS.md` — **지도다. 매뉴얼이 아니다.**
   - 이 저장소가 무엇인가
   - 원칙: "에이전트가 실수하면 프롬프트를 고치지 말고, 그 실수가 구조적으로
     재발할 수 없도록 시스템을 바꾼다"
   - 파이프라인 (아래)
   - **`guides/`는 온디맨드로 읽는다. 전부 읽지 말 것**
   - `guides/RULES.md`가 계약서임을 명시
   - `CLAUDE.md` 는 `@AGENTS.md` 한 줄 shim

   파이프라인:
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

   **글쓰기 규칙은 `guides/writing.md`에 있다.** AGENTS.md에 재진술하지 말고
   포인터만 둬라.

## 제약

- guides/ 는 **파일 목록만 확인**하고 내용은 필요할 때 읽어라. 지금은 골격만.
- `uv sync` 로 uv.lock 생성 후 **커밋**
- `make setup`, `make test` 동작 확인 후 커밋
```

---

# Phase 1 — convert_callouts

```
Obsidian callout → Tistory HTML 변환기를 만든다.

## 명세

`guides/callouts.md` — 8종 타입, alias 표, 기본 타이틀 표, 제약
`guides/RULES.md` — **CONV-01 ~ CONV-06** 이 변환 계약이다

**두 문서를 정독하라.** 표를 코드로 옮기는 것이 작업의 핵심이다.

## 왜 코드인가

지금까지 이 변환을 LLM이 매번 손으로 했다. 그래서 매번 미묘하게 다르게 나왔고,
같은 글을 Obsidian용/블로그용 두 벌 쓰고 있었다.

실제 발행글에서 그 흔적이 보인다 — 한 파일 안에 Obsidian 문법과 HTML이 섞여 있고,
`**두 개**`를 쓰면 될 것을 `<strong>두 개</strong>`로 썼다.

**결정론적 변환이다. LLM이 할 일이 아니다.**

## 구현

`src/blog_harness/convert_callouts.py`

CLI:
    convert-callouts input.md              # stdout
    convert-callouts input.md -o out.md
    convert-callouts --check input.md      # 진단만. 경고 있으면 exit 1

`[project.scripts]` 에 등록.

## 반드시 지켜라 — RULES.md 의 CONV 계약

**CONV-01 (코드 펜스 보호)**
`guides/callouts.md` 자체가 callout 예시를 ```markdown 블록에 담고 있다.
펜스 안을 변환하면 문서가 망가진다. **놓치면 조용히 데이터가 깨진다.**

**CONV-03 (LaTeX 보호)**
이건 실제로 검증된 버그다:
    보호 안 하면:  $a * b * c$  →  $a <em> b </em> c$
    수식 안의 * 가 기울임으로 오인된다.

변환 순서를 반드시 지켜라:
    1. $...$ 를 placeholder 로 치환
    2. HTML 이스케이프
    3. 인라인 마크다운 변환 (코드 → 굵게 → 기울임 → 링크)
    4. placeholder 복원

**CONV-02 의 근거** (실측 2026-07-11):
Tistory는 <blockquote> 안의 마크다운을 파싱하지 않는다. 백틱을 그대로 두면
리터럴로 노출된다. 하지만 <code> 태그는 정상 렌더된다.
→ **변환기가 미리 <code>로 바꿔놔야 한다.** 이것이 변환기의 존재 이유다.

## 테스트 (tests/test_convert_callouts.py)

**변환기가 틀리면 발행본이 깨진다.** 다음을 커버:

- `guides/callouts.md` §7 의 예시 5개 전부
- alias 전체 (§4 표를 parametrize — 27개)
- 8종 기본 타이틀 (§3 표)
- foldable 마커 무시
- **코드 펜스 보호** ← 가장 중요
- **LaTeX 보호** — `$a * b * c$` 가 안 깨지는지
- 일반 blockquote 미변환 (`> 그냥 인용문`)
- 중첩 callout 평문화 + `[!tip]` 마커 제거 + 경고
- HTML 이스케이프 (`<`, `&`)
- 연속 callout 이 병합되지 않는지

## 완료 조건

- pytest 통과, ruff 통과
- Makefile: `make build POST=drafts/foo.md` → `posts/foo.md`
- 커밋
```

---

# Phase 2 — lint_svg

```
다이어그램 SVG 린터를 만든다. **이게 이 저장소의 심장이다.**

## 명세

`guides/RULES.md` — **SVG-01 ~ SVG-09**. 조건·수준·출처가 전부 정의돼 있다.
`guides/diagram-system.md` — 지도
`guides/diagram-patterns/skeleton-layer.md` — SVG-05, SVG-06 의 상세
`guides/diagram-patterns/arrowhead.md` — SVG-07 의 공식

**RULES.md 를 먼저 읽어라. 규칙을 지어내지 마라.**

## 배경

나는 179개 다이어그램을 그리며 규칙을 축적했다. 그런데 지켜지지 않아서 매번 손으로
잡았다. 문서에 이런 표현이 반복 등장한다:

  "Onev 반복 지적"                          (소켓 구분선 접촉)
  "★ 반복 수정 끝에 정립 — 매번 손봄"        (화살촉 공식)

**이 규칙들을 ERROR 메시지로 만드는 것이 이번 작업이다.**

## 구현

`src/blog_harness/lint_svg.py`

stdlib만 사용 (`xml.etree`). 외부 의존성 없이.

CLI:
    lint-svg diagrams/          # 디렉토리 재귀
    lint-svg one.svg
    lint-svg --strict d.svg     # WARN 도 실패로

Exit: 0 = clean, 1 = ERROR (--strict면 WARN 도)

**에러 메시지에 규칙 ID를 출력하라:**
    [ERROR] SVG-06: 타원이 divider(y=250)를 6px 침범. cy=240 를 234 로 ...

규칙 ID로 RULES.md 를 찾을 수 있어야 한다.

## 특히 주의할 규칙

**SVG-01** — 상한은 **900**이다. 720이 아니다.
  (기존 문서에 720으로 적혀 있지만 낡았다. RULES.md 를 따르라)

**SVG-06 (소켓 접촉)** — 가장 중요하다.
  1px 오차도 잡아야 한다. `cy=135, ry=16, divider=150` → 아래변 151 = 침범.
  에러 메시지에 고칠 좌표를 제시하라.
  **divider를 실제로 가로지르는 도형만 검사한다.** 멀리 있는 타원은 대상이 아니다.

**SVG-07 (화살촉)** — WARN이다. ERROR가 아니다.
  검증되지 않은 변형이 있을 수 있다. 수평·수직 표준 화살촉(12×11, 10×5)은 통과시켜라.

**SVG-08 (팔레트)** — **INFO다. WARN도 아니다.**
  단발 색은 정상이다. 누적 카운트만 하고, 3회 이상이면 승격 후보로 보고하라.
  `make palette-report` 타겟을 만들어라.

## false positive 금지 — 절대 규칙

**멀쩡한 것을 잡으면 내가 린터를 무시하게 되고, 그 순간 하네스는 죽는다.**

다음은 반드시 조용히 통과해야 한다:
- `cy = divider_y - ry` 를 정확히 지킨 소켓
- divider 를 가로지르지 않는 타원
- 골격을 안 쓰는 다이어그램 (골격 규칙을 들이대지 마라)
- §3.2 공식대로 계산된 화살촉

## 테스트

**양방향 모두:**

false negative 방지 (잡아야 할 것):
- divider 가운데 걸친 소켓
- **1px 침범 소켓** ← 실제 버그. 에러 메시지에 고칠 좌표(234)가 있는지도 확인
- 금지 유니코드 (parametrize: ₁, ², ⋮)
- viewBox 900 초과
- 잘못된 폰트
- XML 주석의 `--`
- 눈대중 화살촉

false positive 방지 (통과해야 할 것):
- 규격에 맞는 골격 → findings == []
- 정확히 접한 소켓
- divider 에서 먼 타원
- 골격 미사용 다이어그램
- **공식대로 계산한 화살촉**
  (arrowhead.md §3 의 예시 좌표를 그대로: 팁(224,172), 시작(190,140)
   → polygon "224,172 211.8,167.4 218.7,159.5")
- **미등록 색이 있어도 ERROR/WARN 이 아님** (INFO)

## 부수 작업

`diagrams/_template/layer_skeleton.svg` 를 만든다.
`guides/diagram-patterns/skeleton-layer.md` §3 에 SVG 코드가 있다. 그대로 옮겨라.

**문서에만 있고 파일로는 없던 것이다.** 재사용하라고 문서가 말하는데 파일이 없었다.

## 완료 조건

- 테스트 통과 (양방향)
- ruff 통과
- Makefile: `make lint-svg`, `make png` (rsvg-convert -w 2160), `make palette-report`
- 커밋
```

---

# Phase 3 — lint_post

```
발행 전 마크다운 검사기를 만든다.

## 명세

`guides/RULES.md` — **POST-01 ~ POST-11**
`guides/categories.md` — 유효 카테고리 (기계 판독 블록)
`guides/tags.md` — 3축 모델
`guides/writing.md` — 구조 규칙

## 바퀴를 재발명하지 마라

**POST-06 (죽은 링크)는 lychee 를 쓴다.** 직접 짜지 마라.
    https://github.com/lycheeverse/lychee

lychee 가 없으면 안내를 출력하고 **그 검사만 스킵**한다.
**네트워크가 정답성의 의존이 되면 안 된다** — 오프라인에서도 나머지는 돌아야 한다.

## 결정적 설계 — 카테고리를 코드에 박지 마라

`guides/categories.md` 에 기계 판독 블록이 있다:

    <!-- CATEGORIES:BEGIN -->
    Embedded
    C
    ...
    <!-- CATEGORIES:END -->

**이 블록을 파싱하라.** 코드에 상수로 박으면 두 곳을 고쳐야 하고, 그럼 반드시
어긋난다. 실제로 그런 일이 있었다 — OSS Tools 카테고리가 실재하는데 문서에
없었다.

**명세는 한 곳에만 존재해야 한다.**

## 구현

`src/blog_harness/lint_post.py`

stdlib만. CLI:
    lint-post posts/foo.md --category Infra --tags Docker,Ubuntu,정리
    lint-post posts/

frontmatter 는 아직 안 쓴다. 카테고리·태그는 CLI 인자로 받는다.

**에러 메시지에 규칙 ID를 출력하라.**

## 특히 주의할 규칙

**POST-10 (본문 대시)** — 이게 까다롭다.

실측 결과: 발행글 6편에서 대시 77회 중 **본문 산문은 11회뿐**이다.

    IMG 라벨        34회  (허용)
    제목/섹션 부제   30회  (허용)
    본문 산문       11회  ← 이것만 WARN
    표               2회  (허용)

**"대시 금지"로 뭉뚱그리면 false positive 가 66건 난다.**
줄이 `#`, `[IMG:`, `|` 로 시작하면 검사 대상이 아니다.

**POST-09 (마무리)** — WARN이다.
실측: 6편 중 1편이 `## 설치 완료`로 끝나는데, **그게 마무리 역할을 한다.**
ERROR였다면 멀쩡한 글이 차단됐다.

## 테스트

- 유효/무효 카테고리 (CATEGORIES 블록 파싱 포함)
- 태그 3축 각 규칙 (parametrize)
- 카테고리 동명 태그
- 복수형, 주관적 태그, deprecated `삽질`
- 태그 개수 상하한 (Topic 1~6, 총 1~8)
- 이미지 참조 깨짐
- **POST-10: 제목/IMG/표의 대시는 통과, 본문 대시만 WARN**
- 정상 케이스는 조용히 통과

## 완료 조건

- 테스트 통과, ruff 통과
- Makefile: `make lint-post`, `make check` (lint-svg + lychee + lint-post)
- 커밋
```

---

# Phase 4 — factcheck

```
크로스 프로바이더 팩트체커를 만든다.

**코드가 아니라 프롬프트가 산출물이다.**

## 명세

`guides/RULES.md` — **FACT-01 ~ FACT-04**
`guides/writing.md` §2 — 출처 규칙

## 문제

AI가 쓴 글에 출처 없는 주장이 섞인다. 재질문하면 근거가 없었던 경우가 많다.
그래서 매번 내가 직접 검증하고 있다.

실제 발행글에서도 보인다 — "Anima는 20억 파라미터", "512×512부터 1536×1536까지
지원한다" 같은 검증 가능한 수치에 출처가 없다.

**기술 블로그에 없는 출처를 지어낸 주장이 실리면 그건 오염이다.**
축적된 글이 많을수록 비용이 커진다.

## 설계의 핵심 — 이걸 놓치면 전부 무의미하다

GPT에게 팩트체크를 시킨다. **그런데 그냥 시키면 실패한다.**

"출처 없이 사실을 지어냄"은 **Claude와 GPT가 공유하는 실수**다. GPT에게 "이거 맞아?"
라고 물으면 자기 훈련 데이터로 "맞네" 하고 넘긴다.
**프로바이더를 건너서도 에코 챔버가 발생한다.**

그래서 판정 기준을 바꾼다:

    ✗ "이 주장이 사실인가?"        ← GPT의 지식에 의존. 오염됨
    ✓ "글 안에 근거가 있는가?"      ← 텍스트 구조만 본다. 오염 안 됨

**프롬프트에 이 문장을 반드시 넣어라:**

    너 자신의 지식으로 "맞는 것 같다"고 판단하지 마라.
    글 안에 근거가 제시돼 있는지만 본다.

## 판정 카테고리

    VERIFIED      출처가 명시돼 있고 그 출처가 주장을 지지함
    CONTRADICTED  출처와 본문이 어긋남
    UNSOURCED     사실처럼 서술됐지만 출처가 없음          ← 핵심
    HEDGE_NEEDED  통념·경험담인데 단정형으로 쓰임
    EXPERIENCE    1인칭 경험·환경 특정 관찰. 출처 불필요    ← 반드시 넣어라

**EXPERIENCE 가 결정적이다.**

기술 블로그에는 정당하게 출처 없는 문장이 많다:
  - "내 RTX 4060에서는 이 설정이 안 먹었다"
  - "내 PC의 IP가 192.168.0.10인데도 인터넷이 되는 이유는..."

이건 UNSOURCED 가 아니다.
**구분 못 하면 false positive 가 쏟아지고, 그럼 내가 팩트체커를 무시하게 된다.**

`guides/writing.md` §2.1 의 출처 필요/불필요 표를 프롬프트에 넣어라.

## 실패 처리 — 다른 도구에서 배운 것

1. **하드 캡.** MAX_ROUNDS = 3. 루프는 언제나 여기서 종료된다.
2. **교착은 정당한 결과.** 수렴한 척하지 마라. 미해결 주장을 명시하고 사람에게 넘긴다.
   "플래그된 불일치가 가짜 승인보다 낫다."
3. **판정자는 조언한다. 명령하지 않는다.** 최종 결정권은 나에게.
   GPT의 지적을 거부할 땐 이유를 로그에 남긴다.
4. **자동 수정도 자동 통과도 없다.** "플래그는 실패가 아니라 질문이다."
5. **검증 불가능은 삭제가 아니라 완화.** ("~로 알려져 있다", "내 환경에서는")

## 구현

### (a) 기계 부분 — 얇다

`src/blog_harness/factcheck.py`

- 마크다운에서 본문 추출 (코드 블록·IMG placeholder 제외)
- GPT에 보낼 프롬프트 생성 → `factcheck/<slug>.prompt.txt`
- **API를 쓰지 않는다.** 구독 중이고 API 비용을 쓰기 싫다.
  프롬프트를 파일로 뱉으면 내가 GPT 창에 붙여넣는다
- GPT 응답(JSON) 파싱 → 판정 리포트
- 라운드 로그를 `factcheck/<slug>.log.md` 에 append (교착 시 근거)

### (b) 프롬프트 — 진짜 산출물

출력은 파싱 가능한 JSON:

    [
      {
        "claim": "<본문에서 그대로 인용>",
        "verdict": "UNSOURCED",
        "reason": "<왜>",
        "suggestion": "<출처를 달거나 / 완화하거나 / 빼거나>"
      }
    ]

## Makefile

    make factcheck POST=drafts/foo.md
      → factcheck/foo.prompt.txt 생성
      → "GPT에 붙여넣고 응답을 factcheck/foo.response.json 에 저장하세요"

    make factcheck-apply POST=drafts/foo.md
      → response.json 파싱 → 항목별 리포트
      → **자동 수정 금지.** 각 항목을 보여주고 내 판단을 받는다

## 테스트

프롬프트 생성·응답 파싱만 (GPT 호출은 테스트 안 함).
- 본문 추출 (코드 블록 제외)
- JSON 파싱 (깨진 JSON 방어)
- 라운드 캡 (3회 초과 시 교착 보고)

## 완료 조건

- `make factcheck` 로 프롬프트 파일이 나온다
- 프롬프트에 "너 자신의 지식으로 판단하지 마라" 와 EXPERIENCE 카테고리가 있다
- 커밋
```

---

# Phase 5 — 썸네일

```
썸네일 하네스를 만든다. 프롬프트 생성기 + 검증기.

## 명세

`guides/thumbnails.md` — 스타일·오브젝트·13색 매핑·품질 체크리스트
`guides/RULES.md` — **THUMB-01 ~ THUMB-05**

## 문제

가이드가 있는데도 GPT가 매번 다르게 해석해서 일관성이 없다. 강제력이 없기 때문이다.

## 해결 — 프롬프트를 GPT가 만들지 않는다. 하네스가 만든다

지금은 "글 읽고 알아서 썸네일 만들어"를 GPT에게 시킨다. 그래서 매번 다르다.

**가이드가 이미 적용된 완성 프롬프트**를 뱉는다. 나는 복붙만 한다.

### (a) thumbnail_prompt.py

    make thumbnail-prompt POST=drafts/foo.md CATEGORY=Infra

출력: `thumbnails/foo.prompt.txt`

**`guides/thumbnails.md` 의 기계 판독 블록을 파싱하라:**

    <!-- THUMBNAIL_COLORS:BEGIN -->
    | Embedded | `#E0A890` | 살구 코랄 |
    ...
    <!-- THUMBNAIL_COLORS:END -->

카테고리 → 배경색 매핑이다. **코드에 박지 마라.**

프롬프트에 자동으로 박히는 것:
- 스타일 고정 (Pixel art, 16-bit retro)
- 1024×1024, 1:1
- 카테고리 배경색 (위 블록에서)
- 오브젝트 3개 이하
- 텍스트 허용 목록 외 금지
- **금지 스타일 전체 목록** (§4)

개념 → 오브젝트 매핑은 글 내용에서 뽑되, §2.1 표를 참조하라.

### (b) thumbnail_check.py

    make thumbnail-check THUMB=thumbnails/foo.png

RULES.md 의 THUMB-01 ~ THUMB-05 구현.

**THUMB-03 (색상 수)의 임계값은 실측으로 정한다.**
지금 추측으로 박지 마라. 실제 썸네일을 여러 장 돌려보고 결정한다.
일단 느슨하게(예: 8) 시작하고, 조정 가능하게 만들어라.

**THUMB-05 (150px)가 핵심이다.**
가이드 1항이 "150px로 줄여도 무엇인지 보이는가"인데, 지금은 육안으로 상상하고 있다.
**실제로 만들어서 보여준다.**

의존성: Pillow 를 `[project.optional-dependencies]` 에 추가.

### (c) 블라인드 테스트 — 코드가 아니라 워크플로우

`thumbnails/<slug>.150.png` 를 Claude에게 던진다.

**제목·카테고리·생성 프롬프트를 주지 않는다.**

    이 이미지가 무슨 기술 개념으로 보이나? 한 단어로 답하라.
    그리고 이게 "게임 아이템 아이콘"처럼 보이나,
    "기술 개념 아이콘"처럼 보이나?

답이 의도한 개념과 맞으면 PASS. "게임 아이템"이나 "모르겠다"면 REDESIGN.

**판정자에게 정답을 숨기는 것이 설계의 전부다.** 정답을 주면 사후 합리화가
일어난다 — "Docker라니까 Docker처럼 보이네."

GPT가 만들고 **Claude가 판정한다.** 만든 쪽이 채점하면 에코 챔버다.

**AGENTS.md 에 이 절차를 명시하라.**

## 완료 조건

- `make thumbnail-prompt` → 완성된 프롬프트
- `make thumbnail-check` → 기계 검사 + 150px 생성
- AGENTS.md 에 블라인드 테스트 절차
- 커밋
```

---

# Phase 6 — ce-compound (선택)

```
학습 축적 스킬을 이식한다.

## 배경

나는 이미 이걸 수동으로 하고 있었다. 다이어그램 문서의 버전 이력을 보면:

  "동심원 배치 폐기 — 간선이 사방으로 뻗고 라벨이 떠 가독성 나쁨"
  "소켓 구분선 접촉 1px 검산 — cy=135면 아래변 151로 선 1px 침범"

**이게 정확히 Learning 이다.** 문제 → 실패한 시도 → 근본 원인 → 해결 → 재발 방지.
`ce-compound` 의 bug track 섹션 구조와 1:1로 대응한다.

## 할 일

CE 플러그인(github.com/EveryInc/compound-engineering-plugin)에서 `ce-compound`
스킬만 가져온다.

    skills/ce-compound/ → ~/.claude/skills/ce-compound/

SKILL.md 정리:
- `ce-compound-refresh` 참조 제거 (그 스킬을 안 가져오므로 dangling reference)
  Phase 2.5 를 제거하거나 "수동 검토" 노트로 대체
- `/ce-plan`, `/ce-code-review`, `/ce-simplify-code` 언급 제거

**Discoverability Check 는 반드시 살려라.** 이게 AGENTS.md 에 `docs/solutions/` 를
등록해준다. 없으면 학습이 쌓이기만 하고 아무도 안 읽는 무덤이 된다.

## 검증

첫 실행은 **Lightweight 모드**로. Full 모드는 서브에이전트 3개 + grounding
validation 이라 토큰을 꽤 먹는다.

산출물이 쓸만한지 보고 판단한다.
```

---

# 부록

## 진행 체크리스트

| Phase | 산출물 | 완료 |
|---|---|---|
| 사전 | guides/ 19개 이관 | ☐ |
| 0 | 저장소 골격, uv, AGENTS.md | ☐ |
| 1 | convert_callouts (CONV-01~06) | ☐ |
| 2 | lint_svg (SVG-01~09) + layer_skeleton.svg | ☐ |
| 3 | lint_post (POST-01~11) + lychee | ☐ |
| 4 | factcheck 프롬프트 | ☐ |
| 5 | thumbnail_prompt + check + 블라인드 | ☐ |
| 6 | ce-compound 이식 | ☐ |

## 전 Phase 공통 원칙

각 세션에서 상기시킬 것:

1. **`guides/RULES.md` 가 계약서다.** 규칙을 지어내지 마라.
   여기 있는 것만 코드가 되고, 여기 없는 것은 검사하지 않는다.

2. **false positive 금지.** 멀쩡한 것을 잡으면 사람이 린터를 무시하게 되고,
   그 순간 하네스는 죽는다. 애매하면 ERROR가 아니라 WARN. WARN도 애매하면 INFO.

3. **린터 자체를 테스트한다.** 거짓말하는 하네스는 없느니만 못하다.
   false negative(놓침)와 false positive(오탐) 양방향 모두 테스트하라.

4. **런타임 의존성 최소.** 하네스는 **rippable** 해야 한다.
   모델이 좋아지면 절반은 버리게 된다. 의존성이 적을수록 버리기 쉽다.

5. **명세는 한 곳에만.** 카테고리·색 매핑은 문서의 기계 판독 블록을 파싱하라.
   코드에 상수로 박으면 두 곳이 어긋난다.

6. **바퀴를 재발명하지 마라.**
   죽은 링크 = lychee / AI 티 = im-not-ai / 학습 축적 = ce-compound.
   자작하는 건 "세상에 없는 내 도메인 규칙"뿐이다.

7. **에러 메시지에 규칙 ID를.** `[ERROR] SVG-06: ...` 로 출력하라.
   규칙 ID로 RULES.md 를 찾을 수 있어야 한다.
