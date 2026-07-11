# 카테고리

Tistory 블로그(`onebrotravel.tistory.com`)의 카테고리 체계와 귀속 원칙.

이 문서는 **명세**다. 편수·공개 여부·결정 이력은 여기 없다 (그건 블로그 운영 문서에 있다).
린터는 아래 `CATEGORIES` 블록을 파싱한다.

---

## 1. 구조

Tistory는 2계층(대분류/소분류)만 지원한다. 사이드바의 섹션 라벨
(Development / Computer Science / Tools & Infra / Works)은 **hELLO 스킨의 Pug 레이어**이지
Tistory 카테고리가 아니다.

```
Development
  Embedded
  Language          ← 컨테이너. 글이 직접 붙지 않는다
    ├─ C
    └─ Python
  Web

Computer Science
  OS
  Network
  DSA

Tools & Infra
  DevTools
  Infra
  Linux
  OSS Tools

Works
  Projects
  Interests         ← 컨테이너. 글이 직접 붙지 않는다
    └─ ComfyUI
```

### 컨테이너 카테고리

`Language`와 `Interests`는 **컨테이너**다. 소분류를 묶기만 하고 글이 직접 붙지 않는다.
(Tistory 관리 화면의 대분류 편수는 소분류 합산값이다 — Language 19편 = C 19편)

글에 붙는 카테고리는 소분류다: `C`, `Python`, `ComfyUI`.

---

## 2. 유효 카테고리 (린터가 읽는 블록)

글이 실제로 붙을 수 있는 카테고리. **여기 없는 카테고리를 쓰면 ERROR.**
Tistory에 카테고리를 새로 만들면 이 블록에 한 줄 추가한다.

<!-- CATEGORIES:BEGIN -->
Embedded
C
Python
Web
OS
Network
DSA
DevTools
Infra
Linux
OSS Tools
Projects
ComfyUI
<!-- CATEGORIES:END -->

### 미생성 (글 발생 시점에 생성)

첫 관련 글을 쓸 때 그 자리에서 만들고, 위 블록에 추가한다.

| 카테고리 | 자리 | 트리거 |
|---|---|---|
| Cloud | Tools & Infra | AWS 등 관리형 클라우드 첫 글 |
| Experience | Works | 정글 회고 첫 글 |
| 블로그 | Works | 스킨 커스텀·이전기 첫 글 |
| Motion Capture | Works > Interests | 모션캡쳐 첫 글 |
| Coffee | Works > Interests | 커피 첫 글 |

---

## 3. 귀속 원칙

### 3.1 카테고리 = 영구 지식 도메인

> **카테고리 = 평생 들고 갈 지식의 큰 덩어리**
> **시리즈 = 특정 강의·책·프로젝트를 관통하는 일회성 궤적**

강의명·책명은 카테고리에 쓰지 않는다. **Source 태그**로 처리한다.
(`guides/tags.md` 참조)

### 3.2 "무엇을 하는 글인가" 원칙

같은 대상이라도 **글이 무엇을 하는가**로 카테고리가 갈린다. 도구나 하드웨어가
기준이 아니다.

| 대상 | 글의 성격 | 카테고리 |
|---|---|---|
| Raspberry Pi | 서버로 활용 (셀프호스팅) | Infra |
| Raspberry Pi | 센서 제어 (GPIO) | Embedded |
| SearXNG | 셀프호스팅해서 써본 사용기 | OSS Tools |
| SearXNG | PR 보낸 기여 경험 | Projects |
| Docker | 상시 가동 서비스 스택의 기반 구축 | Infra |
| Docker | 로컬 개발환경 구성 | DevTools |

**같은 도구라도 글의 성격이 다르면 다른 카테고리다.**

### 3.3 경계 기준

**OS vs Linux**
- **OS** (Computer Science) — 운영체제 **이론**. 가상 메모리, 프로세스, 스케줄링
- **Linux** (Tools & Infra) — 배포판 **실사용·운영**. 설치, 부트로더, 셸, 개발환경

배포판·버전은 Source 태그가 아니라 `Ubuntu` 등 **Topic 태그**로 식별한다.

**DevTools vs OSS Tools**

구분선은 **"개발환경 구성에 필요한 도구인가"**다. "오픈소스인가"로는 안 갈린다
(tmux도 오픈소스다).

- **DevTools** — 개발환경을 이루는 구성요소. 없으면 개발 작업 자체가 불편해지는 것.
  tmux, git, shell, Neovim
- **OSS Tools** — 그 외 오픈소스 사용기. 개발환경의 일부가 아니라, 어떤 목적을 위해
  갖다 쓰는 것. Firecrawl, flameshot

경계 사례 — **Firecrawl**: Claude Code에 MCP로 붙여 쓰니 개발 도구처럼 보이지만,
본질은 웹 스크래핑 서비스다. 개발환경 자체를 이루는 구성요소가 아니라 필요할 때
갖다 쓰는 서비스다. → **OSS Tools**

**DevTools vs Linux**

OS를 옮겨도 따라가는 도구 지식이면 **DevTools**. tmux의 session 모델·copy-command·
terminal-overrides는 배포판과 무관하다. Ubuntu 특수성(Wayland·GNOME Terminal·IBus)은
환경 맥락이므로 `Ubuntu` Topic 태그가 담당한다.

**OSS Tools vs Projects**

- **OSS Tools** — 도구를 **써본** 기록 (설치·세팅·사용)
- **Projects** — 도구에 **기여한** 기록 (PR, 번역, 문서화)

ComfyUI 문서 한국어 현지화 PR, Flexcyon 테마 번역 PR — 전부 Projects다.

---

## 4. 승격 규칙

같은 오픈소스 도구로 글이 계속 나오면 **개별 카테고리로 승격**한다.

- **임계**: 5편 이상
- **선례**: ComfyUI (지속 사용 → 5편+ → Interests 아래 독립 카테고리)
- **승격 대상이 아닌 것**: Firecrawl, flameshot처럼 한 편 쓰고 소재가 소진되는 도구.
  이런 것들이 OSS Tools에 모인다

승격 시 Tistory에서 부모만 변경하면 되므로 **글 이동 비용은 거의 없다.**

같은 패턴이 팔레트에도 적용된다 (`guides/diagram-system.md` — 미등록 색이 3회 이상
등장하면 Core 승격 검토). **반복이 규칙을 만든다.**

---

## 5. 운영 규칙

- **글 3편 미만 카테고리는 비공개** — 빈 카테고리를 독자에게 노출하지 않는다
- **카테고리 이름은 영문 플레인** — URL 가독성 (`/category/Embedded`).
  이모지·한글 병기 없음
- **카테고리와 동명 태그 금지** — 카테고리는 도메인, 태그는 횡단 조회.
  역할이 겹치면 안 된다 (`guides/tags.md` 참조)
