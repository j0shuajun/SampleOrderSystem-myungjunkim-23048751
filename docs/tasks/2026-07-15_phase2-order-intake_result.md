# Phase 2: 주문 접수와 상태 모델 — 결과

Written at (KST): 2026-07-15 13:20

## 1. 한눈에 보는 요약

주문 접수 시 `RESERVED` 상태로 자동 기록되고, `ORD-YYYYMMDD-NNNN` 형식의 주문번호가
자동 채번된다. 등록되지 않은 시료로는 주문할 수 없다.

## 2. 왜 필요했는지

PRD의 "흐름 A/B" 시나리오는 전부 "고객이 주문을 접수하면 `RESERVED`가 된다"에서
시작한다. 승인/거절(Phase 3)이 판단할 대상 자체가 없으면 이후 Phase를 검증할 수
없으므로, 접수 단계를 먼저 확정해야 했다.

## 3. 예시로 보는 결과

- `S-001`(실리콘 웨이퍼)을 "삼성전자 파운드리"가 200개 주문 → `Order(order_id="ORD-
  20260715-0001", ..., status="RESERVED")` 생성.
- 같은 날 두 번째 주문은 자동으로 `-0002`가 된다. 실패한 주문 시도는 번호를
  소비하지 않는다(확인됨).
- 등록되지 않은 `S-999`로 주문 시도 → `UnknownSampleError` 발생, 주문 생성 안 됨.

## 4. 변경 내용

- `sample_order/domain.py`: `Order` 데이터클래스
- `sample_order/services.py`: `OrderService`(`place_order`/`list_all`),
  `UnknownSampleError`, `SampleService.exists()`

## 5. 검증 결과

- Test Verify: `pytest -q` → 8 passed. 추가로 스크립트를 직접 실행해 같은 날 여러
  주문의 일련번호 증가와 실패 시 번호가 소비되지 않는 것을 확인. PASS
- Compliance Verify: PLAN.md Phase 2 요구사항 4항목 모두 Satisfied. PASS

## 6. 영향 범위

Phase 3(승인/거절)이 이 `Order`/`OrderService`를 기반으로 상태를 전이시킨다.

## 7. 제약/후속

- 승인/거절, 재고 확인은 다음 Phase에서 다룬다.

## 8. Lessons

주문 ID에 날짜가 들어가는 형식이라 테스트가 실제 시각에 의존하면 매일 실패할 뻔했다.
Phase 5(생산완료 시간판정)에서 쓰기로 한 "주입 가능한 `now` 콜러블" 패턴을 여기서
미리 적용해 문제를 피했다 — 시간에 의존하는 로직은 처음 등장할 때부터 시간 소스를
주입 가능하게 만드는 편이 낫다는 게 이번 교훈이다.
