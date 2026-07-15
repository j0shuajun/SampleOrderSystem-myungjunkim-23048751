# Phase 3: 승인/거절 — 계획

Written at (KST): 2026-07-15 14:00

## 1. 목적

접수(`RESERVED`)된 주문을 담당자가 승인 또는 거절할 수 있어야 한다. 승인 시
재고가 충분하면 바로 `CONFIRMED`(출고 대기)가 되고, 부족하면 생산이 필요하다는
뜻으로 `PRODUCING`이 된다(실제 생산 큐 등록은 Phase 4). 이번 Phase의 핵심은
"이중 확정을 막는 가용재고 계산"을 승인 로직에 실제로 연결하는 것이다.

## 2. 현재 상태

`OrderService.place_order`로 `RESERVED` 주문만 만들 수 있고, 승인/거절 기능이
없다.

## 3. 목표 상태

- `OrderService.approve(order_id)`:
  1. 대상 주문이 `RESERVED`가 아니면 실패(`InvalidOrderStateError`).
  2. 가용재고(SPEC.md 5.1) = `sample.stock - (같은 시료의 다른 PRODUCING/CONFIRMED
     주문 수량 합계)`를 계산한다. `RESERVED` 주문은 포함하지 않는다.
  3. 가용재고 ≥ 주문 수량이면 `CONFIRMED`, 아니면 `PRODUCING`으로 바꾼다(생산 큐
     등록 자체는 Phase 4에서 추가).
- `OrderService.reject(order_id)`: `RESERVED`가 아니면 실패, 맞으면 `REJECTED`.

## 4. 예시로 이해하기

**이중 확정 방지 예시** (SPEC.md 5.1과 동일한 숫자):
재고 70인 시료에 주문 A(100개)가 이미 `PRODUCING` 상태로 있다고 하자(=이미
승인된, 미출고 100개). 이제 주문 B(20개)를 승인하면:

```
committed = 100 (A의 수량, PRODUCING이므로 포함)
available = max(0, 70 - 100) = 0
0 < 20  ->  B도 CONFIRMED가 아니라 PRODUCING이 된다
```

raw 재고만 보면 70 ≥ 20이라 착각하기 쉽지만, A가 이미 그 70을 "선점"했으므로 B는
CONFIRMED될 수 없다.

**재고 충분 예시**: 재고 500인 시료에 다른 미출고 주문이 없다면, 50개 주문은
`available = 500 - 0 = 500 ≥ 50`이므로 바로 `CONFIRMED`.

**거절 예시**: `RESERVED` 주문을 거절하면 `REJECTED`. 이미 `REJECTED`인 주문을
다시 승인/거절하려 하면 실패한다.

## 5. 접근 방식

1. `tests/test_sample_order_services.py`(또는 phase 규모상 필요하면 새 파일)에
   4가지 시나리오 테스트 추가: 재고충분→CONFIRMED, 이중확정방지(가용재고 부족)→
   PRODUCING, 거절→REJECTED, RESERVED가 아닌 주문 승인/거절 시도→실패.
2. `sample_order/services.py`에 `OrderService.approve`/`reject`,
   `InvalidOrderStateError` 추가. 가용재고 계산 함수는 재사용 가능하도록 별도
   함수(`_available_stock(sample_id, excluding_order_id)`)로 분리한다.
3. `OrderService`가 이제 시료의 `stock` 값을 읽어야 하므로, 생성자에 넘겨받은
   `sample_service`에서 `sample_id`로 `Sample`을 조회하는 기능이 필요하다 — 이미
   있는 `SampleService`에 `find(sample_id)` 같은 조회 메서드가 없다면 추가한다.

## 6. 가정/리스크/트레이드오프

- 이번 Phase에서 `PRODUCING`이 되어도 아직 생산 작업(Production Job)을 만들지
  않는다. Phase 4에서 "부족분/계획생산량/시작시각"을 가진 생산 작업을 추가로
  생성하도록 확장한다. 지금은 상태 전이만 맞춘다.
- 테스트에서 "이미 PRODUCING인 주문"은 실제 승인 로직을 거치지 않고 픽스처로
  직접 만들어(주문 리스트에 미리 추가) 가용재고 계산만 검증한다. 이는 SPEC.md
  5.1의 committed 정의(PRODUCING/CONFIRMED만 포함, RESERVED 제외)를 그대로
  따르기 위함이다.

## 7. 검증 방법

- 4개 대표 시나리오가 모두 테스트로 통과하는지 확인.
- `RELEASE`/`REJECTED` 등 승인 대상이 아닌 상태에서 승인/거절 시도 시 실패하는지
  확인.
