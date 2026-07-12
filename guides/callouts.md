# Callout

Obsidian callout을 Tistory 발행용 HTML로 변환하는 규칙.

이 문서는 **명세**다. `convert_callouts`가 여기 정의된 표를 그대로 구현한다.

---

## 1. 파이프라인

**초안은 Obsidian 문법으로 쓴다. HTML은 빌드 산출물이다.**

```
drafts/<slug>.md          Obsidian 표준 callout 문법
      │
      │  make build
      ▼
posts/<slug>.md           <blockquote class="markdown-callout ...">
      │
      ▼
Tistory 마크다운 에디터에 붙여넣기 → 마크다운 모드로 발행
      │
      ▼
hELLO 스킨이 8종 색·아이콘으로 렌더
```

변환은 **결정론적**이다. LLM이 손으로 하지 않는다.

**callout 안의 마크다운은 변환기가 HTML로 바꾼다.** Tistory가 `<blockquote>` 내부를
파싱하지 않기 때문이다 (§5 참조). callout 밖의 마크다운(`###`, `**굵게**`, `[링크]`,
이미지)은 그대로 남는다 — Tistory가 GFM 기반이라 처리한다.

---

## 2. 문법

```markdown
> [!note] 타이틀
> 본문 줄 1
> 본문 줄 2
```

`> [!타입]`이 callout임을 표시한다. 타이틀은 선택이다.
`> `로 시작하는 줄들이 callout 본문이 된다.

### 타이틀 생략

타이틀을 안 쓰면 **한글 기본 타이틀**이 자동 부여된다.

```markdown
> [!warning]
> 함정이 있다.
```

→ 발행본 타이틀: `주의`

---

## 3. 8종 타입

| 타입 | 기본 타이틀 | 아이콘 | 용도 |
|---|---|---|---|
| `note` | 노트 | 연필 | 일반 노트·부가 설명 |
| `tip` | 팁 | 전구 | 팁·권장 사항 |
| `important` | 핵심 | 동그라미 느낌표 | 핵심 강조 |
| `warning` | 주의 | 삼각 느낌표 | 주의·함정 |
| `danger` | 위험 | 불꽃 | 위험·심각 |
| `example` | 예시 | 플라스크 | 예시·데모 |
| `success` | 완료 | 동그라미 체크 | 성공·완료·결론 |
| `quote` | 인용 | 따옴표 | 인용 (남의 말) |

`tip`과 `important`는 같은 색(청록)이다. Obsidian 표준을 따른 것이며,
아이콘이 달라 시각적으로 구분된다.

---

## 4. Alias

Obsidian에서 어떤 키워드를 쓰든 변환 시점에 8종 중 하나로 정규화된다.

| 쓸 수 있는 키워드 | → 클래스 |
|---|---|
| `note`, `info`, `todo` | `note` |
| `tip`, `hint` | `tip` |
| `important`, `abstract`, `summary`, `tldr` | `important` |
| `warning`, `caution`, `attention` | `warning` |
| `danger`, `error`, `bug`, `failure`, `fail`, `missing` | `danger` |
| `example` | `example` |
| `success`, `done`, `check` | `success` |
| `quote`, `cite` | `quote` |
| `question`, `faq`, `help` | `note` (fallback) |

**의미가 통하는 키워드를 그냥 쓰면 된다.** 변환이 정규화한다.

---

## 5. 본문

### 인라인 마크다운

callout 본문에 마크다운을 쓴다. **변환기가 HTML로 바꾼다.**

| 마크다운 | → 발행본 |
|---|---|
| `` `코드` `` | `<code>` |
| `**굵게**` | `<strong>` |
| `*기울임*` | `<em>` |
| `[텍스트](url)` | `<a href="...">` |
| `$수식$` | 그대로 통과 (KaTeX가 렌더) |

```markdown
> [!important] 시간복잡도
> 평균 `O(log n)`, 최악 `O(log n)`.
```

> **변환기가 왜 필요한가** (실측, 2026-07-11)
>
> Tistory는 `<blockquote>` 안의 **마크다운을 파싱하지 않는다.** 백틱을 그대로 두면
> 리터럴로 노출된다.
>
> ```
> 입력:  <p>인라인 코드 `test = 3`</p>
> 렌더:  인라인 코드 `test = 3`          ← 백틱이 그대로 보인다
>
> 입력:  <p>평균 <code>O(log n)</code>.</p>
> 렌더:  평균 [O(log n)] .               ← 정상. 스킨이 스타일까지 입힌다
> ```
>
> **변환기가 미리 `<code>`로 바꿔놓아야 한다.** 이것이 초안을 Obsidian 문법으로 쓰고
> 빌드하는 이유다.
>
> LaTeX(`$...$`)는 KaTeX가 DOM을 훑어 처리하므로 그대로 통과시킨다.
> **변환기는 `$...$` 안을 건드리지 않는다** — 수식 안의 `*`가 기울임으로 오인되면 안 된다.

### 줄바꿈

각 `> ` 줄이 별도 `<p>`가 된다. 줄마다 단락이 나뉜다.

같은 단락 안에서 줄을 바꾸려면 `<br>`을 직접 쓴다.

---

## 6. 제약

### foldable (`+` / `-`) — 무시된다

```markdown
> [!tip]+ 펼친 상태
> [!note]- 접힌 상태
```

vault에서는 접기/펼치기가 되지만 **발행본은 항상 펼친 상태**다.
마커는 변환 시 제거된다.

### 중첩 callout — 미지원

```markdown
> [!note] 외부
> 외부 본문
> > [!tip] 내부       ← outer만 callout이 되고
> > 내부 본문          ← inner는 평문으로 떨어진다
```

변환기가 경고를 낸다. **쓰지 않는 것이 안전하다.**

### 코드 펜스 안 — 변환하지 않는다

이 문서처럼 callout 예시를 코드 블록에 담을 때, 펜스 안은 그대로 둔다.

---

## 7. 예시

**정의 박스**
```markdown
> [!note] B-Tree
> B-Tree는 자식 노드를 여러 개 가질 수 있는 다진 트리이며,
> 디스크 I/O를 최소화하기 위한 자료구조다.
```

**핵심 박스**
```markdown
> [!important] 시간복잡도
> 평균 `O(log n)`, 최악 `O(log n)`.
```

**함정 박스**
```markdown
> [!warning] 자주 하는 실수
> `==` 는 동등성, `===` 는 일치성 비교다.
```

**인용**
```markdown
> [!quote] Donald Knuth
> Premature optimization is the root of all evil.
```

**결론** (타이틀 생략 → "완료")
```markdown
> [!success]
> 결국 `HashTable`이 평균 O(1) 조회가 가능한 이유는
> 해시 함수가 균등 분포에 가깝게 작동하기 때문이다.
```

---

## 8. 산출 HTML

변환기가 만드는 형태. **직접 쓸 일은 없다** — 참조용이다.

```markdown
> [!important] 시간복잡도
> 평균 `O(log n)`.
```
↓
```html
<blockquote class="markdown-callout markdown-callout-important">
  <p class="callout-title">시간복잡도</p>
  <p>평균 <code>O(log n)</code>.</p>
</blockquote>
```

클래스 두 개(`markdown-callout` + 타입별)가 **둘 다** 필요하다.

---

## 9. 발행 후 깨졌을 때

hELLO **v4.10.15-onev 이상**을 쓴다. 그 아래 버전은 발행 모드에 따라 callout이 깨진다.

| 증상 | 원인 |
|---|---|
| 색이 안 들어옴 | 클래스명 오타. `markdown-callout`과 타입 클래스가 둘 다 있어야 한다 |
| 아이콘이 사각박스 | FA6 로드 실패. 다른 페이지가 정상이면 캐시 문제 — 새로고침 |
| 일반 blockquote 톤 | `<blockquote>`에 `markdown-callout` 클래스가 없다 |

**발행은 마크다운 모드로 한다.** basic 모드 전환은 쓰지 않는다.
