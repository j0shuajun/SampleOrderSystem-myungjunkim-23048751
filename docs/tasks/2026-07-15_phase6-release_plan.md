# Phase 6: 출고 처리 — 계획

Written at (KST): 2026-07-15 17:00

## 1. 목적

`CONFIRMED`(출고 대기) 주문을 실제로 출고 처리해서 재고를 차감하고 `RELEASE`로
전환한다. 이번 Phase가 끝나면 PRD의 흐름 A/B(접수→승인→(생산)→출고)가 코드로
완결된다.

## 2. 현재 상태

주문이 `CONFIRMED`까지는 되지만(직접 승인이든 생산완료를 통해서든), 출고해서
재고를 차감하고 `RELEASE`로 바꾸는 기능이 없다.

## 3. 목표 상태

- `OrderService.release(order_id)`:
  1. 대상 주문이 `CONFIRMED`가 아니면 `InvalidOrderStateError`.
  2. `sample.stock >= order.quantity`가 아니면 `InsufficientStockError`(정상
     흐름에서는 발생하지 않아야 하지만 방어적으로 검사).
  3. `sample.stock -= order.quantity`, 주문 상태를 `RELEASE`로 바꾼다.

## 4. 예시로 이해하기

재고 200인 시료의 `CONFIRMED` 주문(150개)을 출고하면:

```
release(order_id)
-> sample.stock: 200 -> 50
-> order.status: "CONFIRMED" -> "RELEASE"
```

`CONFIRMED`가 아닌 주문(`RESERVED`/`PRODUCING`/`REJECTED`/이미 `RELEASE`)을
출고하려 하면 `InvalidOrderStateError`.

## 5. 접근 방식

1. `tests/test_sample_order_services.py`에 3개 시나리오 추가: 정상 출고(재고 차감
   + RELEASE), `CONFIRMED`가 아닌 주문 출고 시도 실패, (방어적) 재고 부족 시 실패.
2. `sample_order/services.py`의 `OrderService`에 `release(order_id)`,
   `InsufficientStockError` 추가.

## 6. 가정/리스크/트레이드오프

- 재고 부족으로 출고가 막히는 케이스는 SPEC.md도 "정상 흐름에서는 생산 완료 후
  충분해야 한다"고 명시한 대로, 정상 경로에서는 발생하지 않는 방어 코드다. 테스트는
  `CONFIRMED` 주문을 인위적으로 만들어(재고보다 큰 수량) 이 경로만 별도로 확인한다.

## 7. 검증 방법

- 정상 출고 시 재고 차감량과 상태 전환이 정확한지 확인.
- `CONFIRMED`가 아닌 모든 상태에서 출고 시도가 막히는지 확인.
- 재고 부족 방어 코드가 동작하는지 확인.
