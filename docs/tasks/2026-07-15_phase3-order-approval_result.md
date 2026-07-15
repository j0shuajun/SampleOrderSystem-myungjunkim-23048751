# Phase 3: 승인/거절 — 결과

Written at (KST): 2026-07-15 14:30

## 1. 한눈에 보는 요약

`RESERVED` 주문을 승인하면 가용재고 기준으로 `CONFIRMED` 또는 `PRODUCING`이 되고,
거절하면 `REJECTED`가 된다. 이미 생산 중인 다른 주문이 재고를 선점한 경우, 겉보기
재고가 충분해도 새 주문이 함부로 `CONFIRMED`되지 않는다(이중 확정 방지).

## 2. 왜 필요했는지

엑셀/메모장으로 관리하다 겪은 문제(PRD 배경)의 핵심은 "이미 충분한 재고가 있는데
왜 추가 공정이 도는지" 같은 혼란이었다. 이건 여러 주문이 같은 재고를 각자 충분하다고
착각하고 중복으로 확정되기 때문에 생긴다. 이번 Phase가 그 근본 원인을 막는다.

## 3. 예시로 보는 결과

- 재고 500, 다른 미출고 주문 없는 시료에 50개 주문 → 승인 시 바로 `CONFIRMED`.
- 재고 70인 시료에 A(100개)가 이미 `PRODUCING`으로 재고를 선점한 상태에서 B(20개)를
  승인 → raw 재고(70)만 보면 충분해 보이지만 가용재고 `max(0, 70-100)=0 < 20`이라
  B도 `PRODUCING`이 됨(확인됨).
- 경계값 확인: 가용재고와 주문수량이 정확히 같으면(`100==100`) `CONFIRMED`가 됨(확인됨).
- `RESERVED` 주문 거절 → `REJECTED`. 이미 `REJECTED`인 주문을 다시 승인하려 하면
  `InvalidOrderStateError`.

## 4. 변경 내용

- `sample_order/services.py`: `OrderService.approve`/`reject`,
  `_available_stock`(가용재고 계산), `_require_reserved`, `InvalidOrderStateError`,
  `SampleService.find`

## 5. 검증 결과

- Test Verify: `pytest -q` → 12 passed. 추가로 경계값(가용재고==주문수량) 시나리오를
  직접 실행해 `CONFIRMED`로 처리됨을 확인. PASS
- Compliance Verify: PLAN.md Phase 3 요구사항 5항목 모두 Satisfied. PASS

## 6. 영향 범위

Phase 4(생산 큐)가 `PRODUCING` 상태가 된 주문에 실제 생산 작업(부족분/계획생산량/
시작시각)을 연결한다.

## 7. 제약/후속

- 이번 Phase는 상태 전이만 하고, 실제 생산 작업(Production Job) 생성은 Phase 4로
  미룬다.

## 8. Lessons

테스트 픽스처에서 수동으로 주문을 주입할 때, 자동 채번되는 주문 ID와 픽스처 ID가
우연히 겹쳐서 검증이 엉뚱한 객체를 보는 버그가 있었다(둘 다 같은 날짜의 `-0001`).
앞으로 픽스처 ID는 실제 흐름에서 생성될 ID와 겹치지 않도록 의도적으로 다른 값(다른
날짜 등)을 쓴다.
