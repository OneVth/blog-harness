## Round 1 — 2026-07-21 23:34

CONTRADICTED 1, UNSOURCED 9, HEDGE_NEEDED 2 · 통과 VERIFIED 7, EXPERIENCE 2

- [CONTRADICTED] "| `[::]` 등으로 설정 | `[::]:8888:8888` | 지정 주소 | 제한됨 |"
- [UNSOURCED] "`image_proxy`를 켜면 결과 썸네일까지 SearXNG가 대신 받아온다."
- [UNSOURCED] "재부팅 후 자동 복귀도 `restart: always` 한 줄로 설정된다."
- [UNSOURCED] "컨테이너는 첫 `up` 때 `core-config/settings.yml`을 자동 생성하면서 `secret_key`에 무작위 문자열을 채운다."
- [UNSOURCED] "포트 표현식 `${SEARXNG_HOST:+${SEARXNG_HOST}:}${SEARXNG_PORT}:${SEARXNG_PORT}`은 `SEARXNG_HOST`가 비어 있으면 `PORT:PORT`로 접혀 모든 인터페이스(`0.0.0.0`)에 바인딩된다."
- [UNSOURCED] "`SEARXNG_HOST`를 설정하면 바인딩이 그 주소로 제한된다."
- [UNSOURCED] "`?format=json`은 기본 상태에서 HTTP 403을 돌려준다."
- [UNSOURCED] "검색 백엔드로 붙이는 통합은 JSON을 명시적으로 켜야 동작한다."
- [UNSOURCED] "재시작 정책은 공식 compose에 이미 `restart: always`로 들어 있어, 호스트가 재부팅돼도 인스턴스가 다시 뜬다."
- [UNSOURCED] "둘째 줄의 403은 JSON API가 기본값대로 꺼져 있다는 뜻이다."
- [HEDGE_NEEDED] "그래서 각 엔진은 내 IP나 신원을 보지 못한다."
- [HEDGE_NEEDED] "값을 적으면 그 주소로만 바인딩이 제한된다."

## Round 2 — 2026-07-21 23:38

CONTRADICTED 0, UNSOURCED 4, HEDGE_NEEDED 9 · 통과 VERIFIED 14, EXPERIENCE 2

- [UNSOURCED] "그래서 상위 엔진에는 내 IP 대신 SearXNG 인스턴스의 IP가 보인다."
- [UNSOURCED] "다른 서비스가 이미 `0.0.0.0:8080`을 쓰고 있으면 이렇게 실패한다."
- [UNSOURCED] "(`.env.example`이 예시로 보여주는 `[::]`는 IPv6 전 인터페이스라 제한이 아니라는 점에 주의한다.)"
- [UNSOURCED] "`?format=json`은 기본 상태에서 HTTP 403을 돌려준다."
- [HEDGE_NEEDED] "이 셋과 위 매핑 한 줄이 배포 행동을 결정한다."
- [HEDGE_NEEDED] "손으로 secret_key를 채울 필요는 없다."
- [HEDGE_NEEDED] "Docker Compose는 호스트 주소가 없는 매핑을 모든 인터페이스(`0.0.0.0`)에 게시하므로, LAN의 다른 기기에서 접근할 수 있다."
- [HEDGE_NEEDED] "LAN에 열려면 `SEARXNG_HOST`를 주석 처리한 채로 둔다."
- [HEDGE_NEEDED] "검색 백엔드로 붙이는 통합은 JSON을 명시적으로 켜야 동작하니, 필요할 때 켜고 그전까지는 꺼진 채로 둔다."
- [HEDGE_NEEDED] "첫 줄이 200이면 인스턴스가 LAN에 열려 있다."
- [HEDGE_NEEDED] "둘째 줄의 403은 JSON API가 기본값대로 꺼져 있다는 뜻이다."
- [HEDGE_NEEDED] "브라우저로 `http://<홈서버-IP>:8888` 에 붙으면 검색창이 뜨고, 쿼리를 넣으면 여러 엔진 결과가 병합돼 나온다."
- [HEDGE_NEEDED] "마지막 하나는 값을 비워야 LAN 전체에 열린다는 점만 기억하면, 나머지는 공식 기본값 그대로 홈서버 실사용에 쓸 수 있다."

## Round 3 — 2026-07-21 23:39

CONTRADICTED 0, UNSOURCED 4, HEDGE_NEEDED 9 · 통과 VERIFIED 14, EXPERIENCE 2

- [UNSOURCED] "그래서 상위 엔진에는 내 IP 대신 SearXNG 인스턴스의 IP가 보인다."
- [UNSOURCED] "다른 서비스가 이미 `0.0.0.0:8080`을 쓰고 있으면 이렇게 실패한다."
- [UNSOURCED] "(`.env.example`이 예시로 보여주는 `[::]`는 IPv6 전 인터페이스라 제한이 아니라는 점에 주의한다.)"
- [UNSOURCED] "`?format=json`은 기본 상태에서 HTTP 403을 돌려준다."
- [HEDGE_NEEDED] "이 셋과 위 매핑 한 줄이 배포 행동을 결정한다."
- [HEDGE_NEEDED] "손으로 secret_key를 채울 필요는 없다."
- [HEDGE_NEEDED] "Docker Compose는 호스트 주소가 없는 매핑을 모든 인터페이스(`0.0.0.0`)에 게시하므로, LAN의 다른 기기에서 접근할 수 있다."
- [HEDGE_NEEDED] "LAN에 열려면 `SEARXNG_HOST`를 주석 처리한 채로 둔다."
- [HEDGE_NEEDED] "검색 백엔드로 붙이는 통합은 JSON을 명시적으로 켜야 동작하니, 필요할 때 켜고 그전까지는 꺼진 채로 둔다."
- [HEDGE_NEEDED] "첫 줄이 200이면 인스턴스가 LAN에 열려 있다."
- [HEDGE_NEEDED] "둘째 줄의 403은 JSON API가 기본값대로 꺼져 있다는 뜻이다."
- [HEDGE_NEEDED] "브라우저로 `http://<홈서버-IP>:8888` 에 붙으면 검색창이 뜨고, 쿼리를 넣으면 여러 엔진 결과가 병합돼 나온다."
- [HEDGE_NEEDED] "마지막 하나는 값을 비워야 LAN 전체에 열린다는 점만 기억하면, 나머지는 공식 기본값 그대로 홈서버 실사용에 쓸 수 있다."

