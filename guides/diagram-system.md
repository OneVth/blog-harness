# 다이어그램 시스템

블로그 인라인 다이어그램을 일관된 톤으로 만들기 위한 명세.

**이 문서는 지도다. 전부 읽지 마라.** 필요한 패턴만 `diagram-patterns/`에서 골라 읽는다.

린터(`lint_svg`)가 여기 정의된 규칙 중 기계 검증 가능한 것을 강제한다.
규칙 ID는 `RULES.md` 참조.

---

## 1. 기술 스택

| 도구 | 용도 |
|---|---|
| SVG | 작성 형식. 텍스트 에디터로 직접 쓴다 |
| **rsvg-convert** | SVG → PNG (발행용). `apt-get install librsvg2-bin` |
| **Chrome (headless)** | rsvg 없을 때 SVG→PNG 폴백, GIF 프레임 렌더 (§8). 검수는 이걸로 충분 |
| **ffmpeg** | GIF 조립 (§8) |
| Noto Sans CJK KR | 한글 폰트 |

```bash
rsvg-convert -w 2160 diagram.svg -o diagram.png
```

> **cairosvg를 쓰지 않는다.** 한글(특히 작은 bold)을 래스터화할 때 획이 뭉개진다.
> 해상도를 올려도 잔존한다. rsvg-convert는 한글이 또렷하다.

배경은 transparent 기본값을 유지한다 (Tistory 라이트/다크 모드 양쪽에서 무난).

---

## 2. 디자인 토큰

### 2.1 캔버스

| 항목 | 값 |
|---|---|
| **최대 폭** | **900** — 본문 폭(hELLO `너비: 900`)과 같다 |
| 권장 | **콘텐츠에 맞춘다.** 590~900. 과한 우측 여백을 두지 않는다 |
| 높이 | 콘텐츠에 따라 280~480 |
| PNG 변환 | `-w 2160` |

> **900을 넘으면** 브라우저가 `max-width: 900px`로 **축소 렌더한다.** 가로 스크롤이
> 생기는 게 아니라 **이미지가 작아져 텍스트가 안 보인다.**

**모바일**: Tistory가 `max-width: 100%`를 자동 처리한다. 별도 작업 없다.

### 2.2 색 팔레트 (Core)

hELLO 스킨 액센트와 매칭. **두 액센트 + 그레이스케일**이 기본이다.

| 토큰 | 값 | 용도 |
|---|---|---|
| `--accent-blue` | `#5db0d7` | 흐름·진행 (화살표, 액션) |
| `--accent-blue-fill` | `#e8f4fa` | 액션 박스 fill |
| `--accent-orange` | `#ff5544` | 도착지·강조 |
| `--accent-orange-fill-warm` | `#fff7e6` | 도착지 박스 fill |
| `--accent-orange-fill-soft` | `#ffe4e0` | 데이터 채워진 슬롯 fill |
| `--stroke-default` | `#666` | 일반 박스·라인 |
| `--stroke-structure` | `#444` | 구조선 (골격 divider) |
| `--text-primary` | `#2a2a2a` | 본문 텍스트 |
| `--text-secondary` | `#888` | 라벨·보조 |
| `--text-tertiary` | `#aaa` | 희미한 텍스트 |
| `--fill-light` | `#f5f5f5` | 일반 박스 fill |
| `--fill-white` | `white` | 빈 슬롯 |
| `--grid` | `#ddd` | 격자 |

#### 승격 모델

Core 밖의 색은 **금지가 아니다.** 린터가 INFO로 기록만 한다.

```
make palette-report

미등록 색 사용 현황:
  #eef7e0   4회   ← 3회 이상. 승격 검토
  #689523   4회   ← 3회 이상. 승격 검토
  #b19cd9   1회   ← 단발. 그대로 둔다
```

**3회 이상 등장하면 승격을 검토한다.** 자동 등록하지 않는다 —
**"이 색이 무엇을 의미하는가"를 정의해야 Core에 들어간다.**

단발 색을 미리 등록하면 팔레트가 쓰레기통이 된다. **반복이 규칙을 만든다.**

### 2.3 폰트

**`Noto Sans CJK KR, sans-serif` 하나로 통일한다.** monospace는 쓰지 않는다.

| 용도 | 크기 |
|---|---|
| 헤더 (제목) | 13px bold |
| 본문 라벨 (박스 안) | 13~14px |
| 보조 라벨 (단위·메타) | 11~12px |
| 캡션 | 11px |
| 매우 작은 라벨 | 10px |

### 2.4 모양

| 항목 | 값 |
|---|---|
| 박스 라운드 코너 | `rx="4"` |
| 일반 stroke-width | 1.5 |
| 강조 stroke-width | 2 |
| 점선 | `stroke-dasharray="4,3"` |
| 박스 간 간격 | 40~80px |

점선은 **흐름 표시**(액션의 결과·매핑·논리적 연결)에 쓴다.
직접적 데이터 연결(노드 next 포인터 등)은 실선이다.

---

## 3. 절대 규칙

린터가 ERROR로 잡는다. 위반하면 발행하지 않는다.

| 규칙 | 내용 |
|---|---|
| **폭** | viewBox 폭 ≤ 900 |
| **폰트** | 루트 `font-family="Noto Sans CJK KR, sans-serif"` |
| **유니코드** | subscript/superscript(`₁₂₃` `¹²³`), `⋮` 금지 — tofu로 깨진다. `1`, `2`, `...`로 |
| **XML 주석** | 주석 안에 `--` 금지 — SVG 파싱 에러 |
| **골격 좌표** | §3.8 골격 사용 시 divider 좌표 고정 (→ `diagram-patterns/skeleton-layer.md`) |
| **소켓 접촉** | 골격 divider를 타원/원이 가로지르면 안 된다 — `cy = divider_y - ry` |
| **화살촉 공식** | 사선·곡선 화살촉은 방향벡터로 계산 (→ `diagram-patterns/arrowhead.md`) |

> circled number(`①`~`⑨`)는 rsvg-convert에서 정상 렌더된다 (검증됨).

---

## 4. 패턴 카탈로그

**필요한 것만 읽는다.**

| 패턴 | 언제 | 상세 |
|---|---|---|
| **흐름** | "X → 함수 → Y → 매핑" 단방향 | `diagram-patterns/flow.md` |
| **구조** | 두 자료구조의 결합·참조 관계 | `diagram-patterns/structure.md` |
| **시퀀스** | 한 동작의 단계별 진행 | `diagram-patterns/sequence.md` |
| **Before/After** | 상태 변화의 전후 비교 | `diagram-patterns/before-after.md` |
| **조합** | 같은 데이터의 두 표현, 또는 협업 | `diagram-patterns/composite.md` |
| **차트** | 곡률·증가율 직관 (정량 아님) | `diagram-patterns/chart.md` |
| **플로우차트** | 의사결정 트리 | `diagram-patterns/flowchart.md` |
| **집합 분류** | 포함 관계 (A ⊂ B) | `diagram-patterns/set.md` |

### 공통 기법

| 기법 | 상세 |
|---|---|
| **화살촉 좌표** | `diagram-patterns/arrowhead.md` — **사선을 그릴 땐 반드시 읽어라** |
| **재사용 골격** (User/Kernel/H/W) | `diagram-patterns/skeleton-layer.md` |
| **트리 노드** | `diagram-patterns/tree.md` |
| **그래프 (정점·간선)** | `diagram-patterns/graph.md` |

---

## 5. 워크플로우

```
1. 본문 분석 — 그림으로 보완할 부분 식별
2. 레이아웃 스케치 — 폭 결정 (콘텐츠에 맞춰, ≤900)
3. SVG 작성 — diagrams/<domain>/<name>.svg
4. make lint-svg          ← ERROR면 발행 못 한다
5. rsvg-convert -w 2160
6. 눈으로 검증 — 텍스트 잘림, 화살표 각도
7. 본문에 ![alt](name.png) 삽입
```

**SVG가 소스다. PNG는 산출물이다.** PNG는 커밋하지 않는다.

### 5.1 파일명

```
diagrams/<domain>/<name>.svg
```

디렉토리가 도메인을 말한다. **파일명 prefix는 쓰지 않는다.**
소문자·언더스코어·숫자만 쓴다.

### 5.2 본문 삽입 위치

| 다이어그램 성격 | 위치 |
|---|---|
| 전체 멘탈 모델 | 도입 단락 끝 |
| 개념 설명 보조 | 섹션 개념 문단 다음, 코드 직전 |
| 활용 예시 구조 | 예시 코드 직전 |

**다이어그램은 텍스트를 대체하지 않고 보강한다.** 위아래에 항상 prose가 있다.

### 5.3 Tistory 발행

1. 마크다운 에디터에 본문 붙여넣기
2. `![alt](name.png)` 위치에 커서
3. PNG를 드래그앤드롭 → Tistory가 kakaocdn URL로 교체

---

## 6. 제작 원칙

문서화된 교훈. 린터가 못 잡는 것들이다.

- **직각 꺾은선을 선호한다.** 사선은 화살촉 각도가 어긋나기 쉽고 라벨이 겹친다.
  "내려갔다 올라온다" 같은 의미는 Q 곡선보다 직각 꺾은선이 명확하다
- **화살표는 박스 바깥에서 시작하고 도착 박스 앞에서 멈춘다.** 양 끝에 명확한 gap을 둔다
- **라벨 배치는 블록 점유 영역을 먼저 계산하고 빈 교집합에 놓는다.** 눈대중으로 놓으면 겹친다
- **같은 개념은 같은 예제로.** 다이어그램·본문 코드·캡션이 전부 같은 데이터를 써야 한다
- **표기를 통일한다.** 예: 완화/갱신은 `"정점: 옛값 → 새값"` 한 형식으로 (`←`와 `→` 혼용 금지)
- **용어를 통일한다.** "디바이스 드라이버" — "장치 드라이버" 표기 금지
- **정량 정확도가 필요하면 SVG를 쓰지 마라.** 차트 패턴은 곡률 직관용이다.
  정량 분석은 matplotlib

---

## 7. 알려진 제약

| 제약 | 상태 |
|---|---|
| **다크 모드** | PNG는 라이트 모드 기준. 다크 배경에서 흰 박스가 튈 수 있다. **미해결** |
| **인터랙티브 없음** | PNG는 정적. 순서·인과가 중요하면 §8 GIF (또는 외부 링크 visualgo) |
| **폰트** | 시스템 폰트만. SUIT(hELLO 본문 폰트) 미설치 → Noto Sans CJK KR |

---

## 8. 애니메이션 다이어그램 (GIF)

정적 SVG로 한눈에 안 들어오는 개념(순서·인과·조립 실패)은 GIF 움짤로 만든다.
**SVG 파이프라인 밖이다** — `lint-svg` 는 정적 SVG만 검사한다. 예: `dsa/dp_longest_path`.

### 정적이냐 GIF냐 — 판단

**기본은 정적 SVG→PNG.** 가볍고 `lint-svg` 가 검증한다. GIF 는 무겁고 검사 밖이라,
개념이 **순서·시간·인과**여서 한 장에 동시에 담으면 안 읽힐 때만 쓴다.

| 정적 SVG (기본) | 애니메이션 GIF (예외) |
|---|---|
| 상태·구조·분류 (트리·배열·방향 대비) | 과정·조립 실패 (부분해가 어디서 깨지나) |
| ①②③ 번호·화살표로 순서가 한 장에 담긴다 | 단계가 많거나 "동시 비교"를 강요한다 |
| 정량·구조 | 한 걸음씩 따라가야 이해된다 |

**절차**: 정적 한 장으로 그렸을 때 ①②③·화살표로 순서가 담기나? 담기면 정적.
담으려니 패널이 여러 개로 갈라지고 "왼쪽↔오른쪽 비교"가 되면 GIF.
(#04 최장 경로가 그 예 — 2패널 정적은 동시 비교라 안 읽혔고, 5단계 GIF로 풀렸다.)

| 항목 | 값 |
|---|---|
| **소스** | `<name>.gif.html` — 시간을 URL 파라미터(`?t=초`)로 받아 그 순간의 상태(경로 그리기 진행률·강조·페이드)를 그리는 HTML+CSS+JS. 프레임을 결정론적으로 재현한다 |
| **산출물** | `<name>.gif` — **추적한다** (썸네일 PNG 예외처럼 gitignore 대상 아님) |
| **본문** | `[IMG: <name> (애니메이션)]` placeholder. 발행 시 GIF를 드래그 |

### 렌더 파이프라인 (rsvg 아님 — Chrome + ffmpeg)

```bash
# 1) 프레임 렌더 — t 를 0부터 끝까지 1/fps 씩
for f in $(seq 0 150); do t=$(awk "BEGIN{print $f/12}")
  google-chrome --headless=new --screenshot=frames/$(printf %04d $f).png \
    --window-size=660,560 --force-device-scale-factor=2 \
    "file://$PWD/diagrams/dsa/name.gif.html?t=$t"; done
# 2) 팔레트 최적화로 조립 (색 번짐 방지)
ffmpeg -framerate 12 -i frames/%04d.png -vf "scale=700:-1,palettegen=stats_mode=diff" pal.png
ffmpeg -framerate 12 -i frames/%04d.png -i pal.png \
  -lavfi "scale=700:-1[x];[x][1:v]paletteuse=dither=sierra2_4a" -loop 0 name.gif
```

### 함정 (검증됨)

- **CSS 스타일시트가 JS `setAttribute` 를 덮어쓴다.** 프레임별 `stroke-dashoffset` 은 반드시
  인라인 스타일(`el.style.strokeDashoffset`)로 설정한다. 스타일시트 규칙(`.path{...}`)이
  프레젠테이션 속성보다 우선하므로, `setAttribute` 로 그리면 경로가 안 그려진다.
- **라벨은 선·노드와 겹치지 않게** 빈 공간에 놓는다 (제작 원칙 §6). 프레임을 실제로 렌더해
  눈으로 확인한다 — 정적 SVG보다 겹침이 잘 보인다.
- **정량 애니메이션은 남용하지 않는다.** 트리·배열처럼 정적으로 이미 명확한 건 SVG로 둔다.
  움짤은 "순서로 풀어야 이해되는" 개념에만 쓴다.
