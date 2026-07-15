# Phase 2: 주문 접수와 상태 모델 — 결과

Written at (KST): 2026-07-15 13:20

## 1. 요약

주문 접수 시 `RESERVED` 상태로 자동 기록되고, `ORD-YYYYMMDD-NNNN` 형식의 주문번호가
자동 채번된다. 등록되지 않은 시료로는 주문할 수 없다.

## 2. 예시로 보는 결과

- `S-001`(실리콘 웨이퍼)을 "삼성전자 파운드리"가 200개 주문 → `Order(order_id="ORD-
  20260715-0001", ..., status="RESERVED")` 생성.
- 같은 날 두 번째 주문은 자동으로 `-0002`가 된다. 실패한 주문 시도는 번호를
  소비하지 않는다(확인됨).
- 등록되지 않은 `S-999`로 주문 시도 → `UnknownSampleError` 발생, 주문 생성 안 됨.

## 3. 변경 내용

- `sample_order/domain.py`: `Order` 데이터클래스
- `sample_order/services.py`: `OrderService`(`place_order`/`list_all`),
  `UnknownSampleError`, `SampleService.exists()`

## 4. 검증 결과

- Test Verify: `pytest -q` → 8 passed. 추가로 스크립트를 직접 실행해 같은 날 여러
  주문의 일련번호 증가와 실패 시 번호가 소비되지 않는 것을 확인. PASS
- Compliance Verify: PLAN.md Phase 2 요구사항 4항목 모두 Satisfied. PASS

## 5. 영향 범위

Phase 3(승인/거절)이 이 `Order`/`OrderService`를 기반으로 상태를 전이시킨다.

## 6. 제약/후속

- 승인/거절, 재고 확인은 다음 Phase에서 다룬다.
