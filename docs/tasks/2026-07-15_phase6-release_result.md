# Phase 6: 출고 처리 — 결과

Written at (KST): 2026-07-15 17:30

## 1. 한눈에 보는 요약

`CONFIRMED` 주문을 출고하면 재고가 주문 수량만큼 줄고 상태가 `RELEASE`가 된다.
이로써 접수→승인→(생산)→출고 전체 흐름이 코드로 완결됐다.

## 2. 왜 필요했는지

PRD의 흐름 A/B 모두 "출고 처리 후 주문 상태가 RELEASE가 되고 재고가 차감된다"로
끝난다. 이 마지막 단계가 없으면 지금까지 만든 접수/승인/생산이 실제 업무 흐름을
완성하지 못한다.

## 3. 예시로 보는 결과

재고 300인 시료에 120개 주문을 접수→승인(가용재고 충분해 바로 `CONFIRMED`, 이
시점 재고는 그대로 300)→출고하면:

```
release(order_id)
-> 재고: 300 -> 180
-> 주문 상태: CONFIRMED -> RELEASE
```

`CONFIRMED`가 아닌 주문(`RESERVED` 등)을 출고하려 하면 `InvalidOrderStateError`.
재고가 인위적으로 부족해진 경우엔 `InsufficientStockError`로 막힌다(정상 흐름에서는
발생하지 않는 방어 코드).

## 4. 변경 내용

- `sample_order/services.py`: `OrderService.release`, `InsufficientStockError`

## 5. 검증 결과

- Test Verify: `pytest -q` → 23 passed. 추가로 접수→승인→출고 전체 흐름을 직접
  실행해 재고가 승인 시점엔 그대로이고 출고 시점에만 차감됨을 확인. PASS
- Compliance Verify: PLAN.md Phase 6 요구사항 4항목 모두 Satisfied. PASS

## 6. 영향 범위

Phase 7(모니터링)이 이제 `RELEASE`까지 포함한 전체 상태 분포를 집계할 수 있다.

## 7. 제약/후속

- 모니터링(상태별 집계, 재고 상태)은 Phase 7에서 다룬다.

## 8. Lessons

특이사항 없음 — SPEC.md 7장의 조건/결과가 그대로 구현 체크리스트가 되어 모호함이
없었다.
