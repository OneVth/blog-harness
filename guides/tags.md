# 태그

Tistory 태그 컨벤션.

이 문서는 **명세**다. 린터(`lint_post`)가 여기 정의된 규칙을 강제한다.

---

## 1. 원칙

- **카테고리는 도메인, 태그는 횡단 조회.** 카테고리와 동명 태그를 쓰지 않는다
- **같은 개념 = 같은 태그.** 한 개념을 글마다 다르게 부르지 않는다
- **태그는 검색 유입 경로다.** 독자가 실제로 검색창에 칠 말로 짓는다

---

## 2. 3축 모델

| 축 | 개수 | 필수 | 내용 |
|---|---|---|---|
| **Topic** | 1~6 | ✅ | 글의 핵심 개념. 고유명 포함 |
| **Source** | 0~1 | | 강의·책 출처 |
| **Kind** | 0~1 | | 글의 형식 |

**글당 총 1~8개.**

---

## 3. 축 1 — Topic

글의 핵심 개념. 고유명(`정글`, `SnapAgent`, `Firecrawl`)도 Topic이다.

### 3.1 영문·한글 혼용

**독자가 양쪽으로 검색할 개념이면 둘 다 붙인다.**

```
✓ Array, 배열
✓ Pointer, 포인터
✓ HashTable, 해시테이블
✓ VirtualMemory, 가상메모리
```

한쪽만 통용되면 하나만 붙인다.

```
✓ TCP              (한글 "티씨피"로 검색하지 않는다)
✓ NvChad           (고유명)
✓ 듀얼부팅          (영문 대응이 어색하다)
```

혼용은 **선택**이다. 강제하지 않는다.
다만 **한 개념에 대해 글마다 다르게 하지는 않는다** — 그러면 URL이 분열된다.

### 3.2 표기 규칙

| 종류 | 규칙 | 예 |
|---|---|---|
| 언어·기술 | 공식 표기 | `C`, `Python`, `TypeScript`, `STM32`, `Git` |
| 프로토콜·표준 | 대문자 축약 유지 | `TCP`, `HTTP`, `SSL`, `I2C`, `GPIO` |
| 개념 (복합어) | PascalCase | `HashTable`, `DynamicProgramming`, `VirtualMemory` |
| 개념 (단일어) | 그대로 | `Algorithm`, `Sort`, `Pointer` |
| 제품·OS | 공식 표기 | `RaspberryPi`, `Ubuntu`, `macOS`, `Neovim` |
| 고유명 | 원래 이름 | `정글`, `SnapAgent`, `Firecrawl` |

---

## 4. 축 2 — Source

강의·책 출처. **원제 언어**를 따른다. 한국어 원제는 한글 축약을 허용한다.

| 태그 | 출처 |
|---|---|
| `CSAPP` | Computer Systems: A Programmer's Perspective |
| `OSTEP` | Operating Systems: Three Easy Pieces |
| `CLRS` | Introduction to Algorithms |
| `ProGit` | Pro Git |
| `DoItAlgorithm` | Do it! 알고리즘 코딩테스트 |
| `MissingSemester` | MIT Missing Semester |
| `넓얕CS` | 넓고 얕게 배우는 CS |
| `OJTube임베디드` | OJTube 임베디드 강의 |
| `독하게시작하는C프로그래밍` | 독하게 시작하는 C 프로그래밍 |

**명명 패턴**: 한 채널이 여러 강의를 냈으면 `{채널명}{강의주제}`.
`OJTube` 단독으로는 강의를 구분할 수 없다.

---

## 5. 축 3 — Kind

글의 형식. **0~1개.** 회고면서 정리인 글은 없다 — 주된 성격 하나만 고른다.

| 태그 | 용도 |
|---|---|
| `회고` | 프로젝트·기간 회고 |
| `정리` | 책·강의 정리 노트 가공본 |
| `트러블슈팅` | 문제 해결 |
| `입문` | 해당 주제 첫걸음 가이드 |

감정·과정 서사는 **본문 톤**이 담당한다. 태그가 담당하지 않는다.

### deprecated

| 태그 | 상태 |
|---|---|
| `삽질` | **신규 사용 금지.** `트러블슈팅`으로 통일. 기존 글은 소급 수정하지 않는다 |

---

## 6. DON'T

전부 린터가 ERROR로 잡는다.

| 금지 | 예 | 이유 |
|---|---|---|
| **카테고리 동명 태그** | `Embedded`, `DSA`, `Projects` | 카테고리는 도메인, 태그는 횡단 조회. 역할이 겹친다 |
| **복수형** | `Arrays` ✗ → `Array` | URL 분열 |
| **주관적 태그** | `추천`, `꿀팁`, `핵심` | 검색어가 아니다 |
| **개인 분류 태그** | `기억할것`, `공부`, `type/생성` | Obsidian용이지 블로그용이 아니다 |
| **강의 내 실습 주제** | `고추건조기` | 실습마다 태그가 생긴다. Source 태그로 묶이니 충분하다 |
| **`삽질`** | (deprecated) | `트러블슈팅`으로 통일 |

---

## 7. 예시

| 글 | 카테고리 | 태그 |
|---|---|---|
| 최신 DS18B20 라이브러리로 고추건조기 리팩토링하기 | Embedded | `STM32`, `DS18B20`, `OJTube임베디드`, `트러블슈팅` |
| GPIO 제어 뿌셔먹기 | Embedded | `STM32`, `GPIO`, `OJTube임베디드` |
| CSAPP 8장 프로세스 제어 핵심 정리 | OS | `Process`, `SystemCall`, `CSAPP`, `정리` |
| 정글 5주차 PintOS 페이지 폴트 삽질기 | OS | `정글`, `PintOS`, `VirtualMemory`, `가상메모리`, `트러블슈팅` |
| SnapAgent 프로젝트 회고 (1) | Projects | `SnapAgent`, `회고` |
| 라즈베리파이 5 초기 설정 가이드 | Infra | `RaspberryPi`, `Linux`, `입문` |
| Ubuntu 26.04 듀얼부팅 설치 | Linux | `Ubuntu`, `듀얼부팅`, `트러블슈팅` |
| Ubuntu에 NvChad 개발환경 구축하기 | DevTools | `NvChad`, `Neovim`, `Ubuntu`, `정리` |
| Firecrawl 셀프호스팅으로 웹 스크래핑 API 무료로 쓰기 | OSS Tools | `Firecrawl`, `SelfHosting`, `Docker`, `정리` |
| 해시 테이블 — collision, chaining | DSA | `HashTable`, `해시테이블`, `CLRS`, `정글`, `정리` |

`정글` 태그가 여러 카테고리(DSA/OS/Network/C)에 분산된 글을 가로질러 묶는다.
`/tag/정글` URL 하나로 학습 여정 전체를 조회할 수 있다.

---

## 8. 개념 사전 (미구현)

영문/한글 쌍의 **일관성**을 검사하려면 개념 사전이 필요하다.

```yaml
# guides/tag-concepts.yaml  (아직 없음)
Array:      [Array, 배열]
Pointer:    [Pointer, 포인터]
TCP:        [TCP]              # 영문만
트러블슈팅:  [트러블슈팅]        # 한글만
```

린터가 이걸 읽으면 *"`Array`를 붙였는데 `배열`이 없다"*를 WARN으로 잡을 수 있다.

**사전이 없는 동안 린터는 영/한 일관성을 검사하지 않는다.**
검사할 근거가 없으면 검사하지 않는다.

사전은 실제 글을 쓰면서 축적한다.
