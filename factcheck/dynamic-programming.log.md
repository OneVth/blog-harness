## Round 1 — 2026-07-14 19:17

CONTRADICTED 2, UNSOURCED 4, HEDGE_NEEDED 2 · 통과 VERIFIED 1, EXPERIENCE 0

- [CONTRADICTED] "파이썬 기본 재귀 한계는 1000이고(`sys.getrecursionlimit()`으로 확인된다), 메모이제이션으로 `fibo_memo(2000)`을 호출하면 재귀가 이 한계를 넘어 `RecursionError`가 난다."
- [CONTRADICTED] "이 갈림은 CLRS의 최적 부분 구조 논의에서 정식으로 다뤄진다."
- [UNSOURCED] "naive 호출 수 자체가 피보나치 수열을 따른다($2 \cdot fib(n+1) - 1$)."
- [UNSOURCED] "즉 호출 수가 지수적으로 증가한다."
- [UNSOURCED] "$$\text{naive 호출 수} = 2 \cdot fib(n+1) - 1 = O(\varphi^n), \quad \varphi \approx 1.618$$"
- [UNSOURCED] "반면 DP의 계산 횟수는 `n-1`로 선형이다."
- [HEDGE_NEEDED] "naive로 `fib(35)`를 구하면 눈에 띄게 느려지고, `fib(50)`은 사실상 끝나지 않는다."
- [HEDGE_NEEDED] "시간 복잡도는 둘 다 $O(n)$으로 같지만, 재귀 깊이가 크면 메모이제이션은 쓸 수 없다."

## Round 2 — 2026-07-14 20:02

CONTRADICTED 0, UNSOURCED 9, HEDGE_NEEDED 4 · 통과 VERIFIED 2, EXPERIENCE 1

- [UNSOURCED] "병합 정렬의 부분 문제(`a[0..2]` 정렬, `a[3..5]` 정렬)는 서로 완전히 분리(disjoint)되어 있어, 캐시를 붙여도 히트가 나지 않는다."
- [UNSOURCED] "| 5 | 5 | 15 | 4 |
| 10 | 55 | 177 | 9 |
| 20 | 6765 | 21,891 | 19 |
| 30 | 832,040 | 2,692,537 | 29 |"
- [UNSOURCED] "풀면 $T(n) = 2 \cdot fib(n+1) - 1$이 되며, 위 표와 맞는다 (검산: $fib(6)=8$이라 $T(5)=15$, $fib(11)=89$라 $T(10)=177$)."
- [UNSOURCED] "호출 수가 피보나치 수를 따르고 $fib(n)$은 $\varphi^n / \sqrt5$로 커지므로, 전체 호출 수는 지수적으로 증가한다."
- [UNSOURCED] "$$\text{naive 호출 수} = 2 \cdot fib(n+1) - 1 = O(\varphi^n), \quad \varphi = \frac{1+\sqrt5}{2} \approx 1.618$$"
- [UNSOURCED] "이 문제에서는 상태를 어떻게 정의하느냐에 따라 전이 식이 맞기도 하고 틀리기도 한다."
- [UNSOURCED] "누적 합이 음수가 되면 버리고 새로 시작하는 것이 Kadane의 핵심이다."
- [UNSOURCED] "최단 경로는 DP가 된다(Floyd-Warshall이 그렇다)."
- [UNSOURCED] "이 갈림은 CLRS(*Introduction to Algorithms*) 3판 §15.3 '동적 계획법의 요소'에서 최적 부분 구조 예시로 다뤄지고(최장 단순 경로 반례가 여기 나온다), 최단 경로 부분 경로의 최적성은 정리 24.1로 정리돼 있다."
- [HEDGE_NEEDED] "DP를 처음 배우면 대개 완성된 점화식부터 만난다."
- [HEDGE_NEEDED] "naive는 `fib(35)` 정도면 눈에 띄게 느려지고, 대략 `fib(50)`을 넘어가면 현실적인 시간 안에 끝나지 않는다."
- [HEDGE_NEEDED] "둘의 실질적 차이는 스택 깊이다."
- [HEDGE_NEEDED] "최단 경로는 정점을 재사용하면 길이만 늘어 손해라 애초에 안 한다."


---

## Round 2 조율 (Claude, FACT-04)

라운드 1의 CONTRADICTED 2건 해소 확인: 파이썬 재귀 한계 → EXPERIENCE, 문서 메커니즘·NP-hard → VERIFIED.

**수용 (4):**
- HEDGE "최단 경로 정점 재사용 손해" → 양의 가중치 전제 명시 (정당한 정밀화).
- HEDGE "둘의 실질적 차이는 스택 깊이" → "피보나치 예제에서 특히 두드러지는" 으로 범위 한정.
- HEDGE "DP 처음 배우면 대개..." → "입문에서는 ~ 경우가 많다" 완화.
- UNSOURCED 호출 수 표 → "직접 세어 보면" 으로 측정 출처 명시 (EXPERIENCE).

**거부 (이유 명시) — writing.md §2.1: 개념 설명·정의·수학적 사실은 출처 불필요:**
- 병합 정렬 disjoint / Kadane 상태·핵심 / Floyd-Warshall DP → 모두 **개념 설명**. §2.1 이 출처 면제.
- T(n) 폐형식·검산 / fib(n)~φⁿ / O(φⁿ) → **본문에 유도·검산이 이미 있다.** 표준 수학이라 외부 출처 불필요.
- CLRS §15.3·정리 24.1 → **정식 서적 인용**(판·절·정리 번호 제시). "링크가 본문을 보여줘야 한다"는 요구는 저작권 서적 인용에 부적절하다. 절 번호가 검증 좌표다.

**판정:** CONTRADICTED 0 도달. 남은 UNSOURCED/HEDGE 는 §2.1 면제 대상이거나 본문 유도로 자기완결. 
FACT-03 대로 개념 설명 플래그를 좇아 라운드를 늘리지 않는다 — 수렴한 척보다 근거 있는 거부가 낫다.
