---
category: OSS Tools
tags: [SearXNG, Docker, 셀프호스팅, 홈서버, 메타검색엔진, 프록시, 입문]
---
<!-- DIAGRAM-LEDGER
SearXNG 프록시 위치 → 그림 (searxng_proxy) | 사용자·SearXNG·상위엔진의 팬아웃과 "각 엔진엔 SearXNG만 보인다"는 공간 관계라 배치가 산문보다 명확
설치 방법 3종 비교 → 표 | 선택지 비교라 3.4 표
compose instancing 절차 → 산문+코드 | 선형 순서라 코드 블록으로 충분
.env 세 변수 역할 → 표 | 변수 대 역할 매핑이라 3.4 표
SEARXNG_HOST 바인딩 → 표+콜아웃 | 값(미설정/설정) 대 바인딩 결과 매핑이라 표, 비워야 열린다는 점은 콜아웃으로 강조
포트 충돌 해결 → 산문+코드 | 실패 메시지와 한 줄 수정이라 문장으로 충분
검증 curl → 산문+코드 | 상태코드 확인이라 코드, 터미널 스크린샷은 코드 블록과 중복이라 불필요
실행 결과 화면 → 스크린샷 | 셋업 가이드의 payoff, "여기까지 하면 이 UI가 뜬다"는 코드·표로 못 보임 (발행 시 PNG 드롭)
IP 숨김 3방법 → 표 | 선택지 비교라 3.4 표, 메시 VPN how-to는 별도 글로 미룸
-->

# SearXNG 셀프호스팅 — 홈서버에 올리는 메타서치 엔진

## 들어가며

SearXNG는 메타서치 엔진이다. 사용자와 상위 검색엔진(Google·Bing·DuckDuckGo…) 사이에 끼는 프록시 겸 애그리게이터로, 쿼리를 여러 엔진에 대신 던지고 결과를 병합해 돌려준다. SearXNG가 서버 쪽에서 대신 요청하므로, 내 브라우저의 쿠키·로그인 세션·핑거프린트가 상위 엔진에 넘어가지 않는다. 상위 엔진은 그 쿼리를 내 신원에 연결하지 못한다. [`image_proxy` 설정](https://docs.searxng.org/admin/settings/settings_server.html)을 켜면 결과 썸네일까지 SearXNG가 대신 받아와, 이미지 서버도 내 브라우저를 직접 보지 못한다.

[IMG: searxng_proxy — 사용자·SearXNG·상위 엔진의 프록시 구조. SearXNG가 검색어를 여러 엔진에 대신 던지고 결과를 병합해 돌려주며, 각 엔진에는 SearXNG만 보인다]

이 글에서는 Docker로 SearXNG를 홈서버에 올려 LAN에서 쓰는 설정을 다룬다. 설치 방법 선택, compose instancing 절차, 배포 행동을 결정하는 `.env` 세 변수, 그리고 흔히 틀리는 지점을 순서대로 본다.

## 설치 방법 고르기

[공식 설치 문서](https://docs.searxng.org/admin/installation.html)는 방법 세 가지를 제시한다.

| 방법 | 방식 | 언제 |
|---|---|---|
| 컨테이너 | Docker compose로 앱·캐시를 격리 실행 | 재현성·재부팅 복귀가 필요하거나, 다른 서비스가 이미 도는 홈서버에 얹을 때 |
| 설치 스크립트 | 호스트에 직접 설치 (uWSGI + systemd) | SearXNG 전용 서버에 표준 구성으로 빠르게 올릴 때 |
| 단계별 설치 | 구성 요소를 하나씩 수동 설치 | 인스턴스 구조를 학습하거나 세부를 직접 통제할 때 |

문서도 특별한 선호가 없으면 컨테이너나 스크립트를 권한다. 이 글은 컨테이너 방식으로 간다. 홈서버에는 이미 다른 서비스가 여럿 돌고 있어서 호스트에 Python 의존성과 uWSGI를 직접 얹기보다 컨테이너로 격리하는 편이 포트·의존성 충돌을 줄인다. 재부팅 후 자동 복귀도 [`restart: always` 정책](https://docs.docker.com/engine/containers/start-containers-automatically/) 한 줄로 설정된다.

## compose instancing으로 올리기

컨테이너 방식의 현재 공식 절차는 compose instancing이다. [Docker 설치 문서](https://docs.searxng.org/admin/installation-docker.html)가 안내하는 대로, 메인 `searxng/searxng` 저장소의 `container/` 파일 두 개를 `curl`로 받아 쓴다.

```bash
mkdir -p ./searxng/core-config/
cd ./searxng/
curl -fsSL \
    -O https://raw.githubusercontent.com/searxng/searxng/master/container/docker-compose.yml \
    -O https://raw.githubusercontent.com/searxng/searxng/master/container/.env.example
cp -i .env.example .env
nano .env
docker compose up -d
```

받아지는 `docker-compose.yml`은 서비스 두 개(앱 서버 core, 캐시 valkey)로 끝난다. 손댈 곳은 포트 매핑 한 줄과 그 줄이 읽는 `.env` 변수다.

```yaml
name: searxng
services:
  core:
    container_name: searxng-core
    image: docker.io/searxng/searxng:${SEARXNG_VERSION:-latest}
    restart: always
    ports:
      - ${SEARXNG_HOST:+${SEARXNG_HOST}:}${SEARXNG_PORT:-8080}:${SEARXNG_PORT:-8080}
    env_file: ./.env
    volumes:
      - ./core-config/:/etc/searxng/:Z
      - core-data:/var/cache/searxng/
  valkey:
    container_name: searxng-valkey
    image: docker.io/valkey/valkey:9-alpine
    command: valkey-server --save 30 1 --loglevel warning
    restart: always
    volumes:
      - valkey-data:/data/
volumes:
  core-data:
  valkey-data:
```

## .env 세 변수가 배포를 결정한다

`.env.example`에는 주석 처리된 변수 세 개뿐이다. 이 셋과 위 매핑 한 줄이 배포 행동을 결정한다.

| 변수 | 기본값 | 역할 |
|---|---|---|
| `SEARXNG_VERSION` | `latest` | 컨테이너 이미지 태그 |
| `SEARXNG_HOST` | (미설정) | 바인딩 주소. 설정 여부에 따라 노출 범위가 달라진다 |
| `SEARXNG_PORT` | `8080` | 호스트 포트와 컨테이너 포트를 함께 지정한다 |

### secret_key는 건드릴 필요 없다

내 환경에서는 첫 `up` 때 `core-config/settings.yml`이 자동 생성되면서 `secret_key`에 무작위 문자열이 채워져 있었다. 생성된 파일은 이게 전부였다.

```yaml
use_default_settings: true
server:
  secret_key: "<무작위 문자열>"
  image_proxy: true
```

손으로 secret_key를 채울 필요는 없다. 생성된 파일을 한 번 열어 확인하면 된다.

### 포트 충돌은 SEARXNG_PORT 하나로 옮긴다

기본 포트는 8080이다. 다른 서비스가 이미 `0.0.0.0:8080`을 쓰고 있으면 이렇게 실패한다.

```text
Error response from daemon: ... Bind for 0.0.0.0:8080 failed: port is already allocated
```

`.env`에서 `SEARXNG_PORT`를 빈 포트로 바꾸면 된다. 매핑이 `${SEARXNG_PORT:-8080}:${SEARXNG_PORT:-8080}`이라 변수 하나로 호스트 포트와 컨테이너 포트가 함께 지정된다.

```bash
# .env
SEARXNG_PORT=8888
```

### LAN 바인딩은 변수를 비워야 열린다

포트 매핑에서 호스트 주소는 채우는 쪽이 아니라 비우는 쪽이 더 넓게 연다. 포트 표현식 `${SEARXNG_HOST:+${SEARXNG_HOST}:}${SEARXNG_PORT:-8080}:${SEARXNG_PORT:-8080}`은 `SEARXNG_HOST`가 비어 있으면 `PORT:PORT`로 접힌다. [Docker Compose의 포트 매핑](https://docs.docker.com/reference/compose-file/services/)은 호스트 주소가 없으면 모든 인터페이스(`0.0.0.0`)에 게시한다. 그래서 호스트 방화벽이 포트를 허용하면 LAN의 다른 기기에서 접근할 수 있다. 반대로 `127.0.0.1` 같은 특정 주소를 적으면 그 주소로만 게시된다.

| `SEARXNG_HOST` | 접히는 매핑 | 게시 주소 | 노출 |
|---|---|---|---|
| 미설정 (주석 유지) | `8888:8888` | `0.0.0.0` | 모든 인터페이스, LAN 접근 가능 |
| `127.0.0.1` | `127.0.0.1:8888:8888` | 루프백만 | 이 머신 안에서만 |

> [!warning] 바인딩을 열려면 변수를 비운다
> 주소를 적어 넣어야 열린다고 생각하기 쉽지만 반대다. 모든 인터페이스에 게시하려면 `SEARXNG_HOST`를 주석 처리한 채로 두고, 방화벽에서 포트를 허용한다. `127.0.0.1`처럼 특정 주소를 적으면 그 주소로만 게시된다.

### JSON API와 재시작 정책

[SearXNG Search API 문서](https://docs.searxng.org/dev/search_api.html)에 따르면, 지원 포맷은 `settings.yml`의 `search:` 섹션에 정의되며 켜지지 않은 포맷을 요청하면 403이 돌아온다. 내 환경의 기본 설정에서는 JSON이 꺼져 있어 `?format=json`이 403이었다. JSON API를 쓰는 통합이라면 이 포맷을 명시적으로 켜야 하니, 필요할 때 켜고 그전까지는 꺼진 채로 둔다.

재시작 정책은 공식 compose에 이미 `restart: always`로 들어 있어 호스트가 재부팅돼도 인스턴스가 다시 뜬다.

## 검증

서버에서 인스턴스가 떴는지, JSON 포맷이 꺼져 있는지 `curl`로 확인한다.

```bash
curl -so /dev/null -w '%{http_code}' localhost:8888/                              # 200
curl -so /dev/null -w '%{http_code}' 'localhost:8888/search?q=test&format=json'   # 403
```

첫 줄이 200이면 인스턴스가 떠 있고, 방화벽이 포트를 허용하면 LAN의 다른 기기에서도 같은 200을 받는다. 둘째 줄의 403은 현재 설정에서 JSON 포맷이 켜지지 않았다는 뜻이다. 통합이 필요해지면 그때 켠다.

설정이 정상 적용됐다면 브라우저로 `http://<홈서버-IP>:8888` 에 붙어 검색창을 볼 수 있고, 쿼리를 넣으면 여러 엔진 결과가 병합돼 나온다.

[IMG: SearXNG 검색 결과 화면 — 실행 인스턴스에서 한 검색어로 여러 엔진 결과가 하나로 병합돼 나온 페이지. 브라우저 탭·주소창은 크롭해 콘텐츠 영역만 담는다 (tailnet 100.x IP 자체는 라우팅 안 되는 저위험이나 화면이 깔끔). 공인 WAN IP·tailnet MagicDNS 도메인 이름은 노출하지 않는다]

## IP까지 가리려면

홈서버 셀프호스팅은 신원은 분리하지만 IP는 가리지 않는다. 내 브라우저도 SearXNG도 같은 홈 공인 IP로 인터넷에 나가기 때문에, 상위 엔진이 보는 IP는 내가 직접 검색할 때와 같다. IP까지 가리려면 SearXNG가 나가는 경로를 집 밖으로 옮겨야 한다.

| 방법 | 상위 엔진이 보는 IP |
|---|---|
| 집 밖 VPS에 호스팅 | VPS의 IP |
| 공개 인스턴스(남의 서버) 사용 | 그 서버의 IP, 여러 사용자가 공유 |
| 홈서버는 두고 나가는 트래픽만 VPN·메시 출구로 | 출구 노드의 IP |

## 마무리

SearXNG 배포는 `.env` 세 변수로 정리된다. `SEARXNG_VERSION`은 이미지 태그, `SEARXNG_PORT`는 충돌을 피하는 포트, `SEARXNG_HOST`는 노출 범위다. 마지막 하나는 값을 비우면 모든 인터페이스에 게시된다는 점만 기억하면 된다. 방화벽에서 포트만 열어주면 나머지는 공식 기본값 그대로 홈서버 실사용에 쓸 수 있다.
