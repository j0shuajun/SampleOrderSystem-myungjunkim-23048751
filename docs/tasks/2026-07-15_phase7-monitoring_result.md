# Phase 7: 모니터링 — 결과

Written at (KST): 2026-07-15 18:30

## 1. 한눈에 보는 요약

주문을 상태별로 집계(REJECTED 제외)하고, 시료별 재고를 여유/부족/고갈 세 가지로
읽기 전용으로 분류하는 `MonitoringService`를 추가했다.

## 2. 왜 필요했는지

운영 담당자가 "지금 어떤 주문이 몇 건씩 있고, 어떤 시료가 재고 위험에 있는지"를
한눈에 봐야 한다는 PRD의 요구를, 지금까지 만든 서비스들을 건드리지 않고 집계만
하는 별도 계층으로 만들었다.

## 3. 예시로 보는 결과

- 6건 주문(RESERVED 2, PRODUCING 1, CONFIRMED 1, RELEASE 1, REJECTED 1) →
  `order_status_counts()` = `{"RESERVED":2,"PRODUCING":1,"CONFIRMED":1,"RELEASE":1}`,
  REJECTED은 아예 안 들어가고 `rejected_count()`로만 확인(=1).
- 재고 20, 미출고 18인 `S-001` → 여유 / 재고 5, 미출고 8인 `S-002` → 부족 /
  재고 0, 주문 없는 `S-003` → 고갈.
- 추가로 test-verifier가 독립적으로 확인: 재고 0인데 미출고 주문이 있어도(0이
  아니어도) 고갈이 우선하고, 주문이 한 번도 없던 시료도 목록에 빠짐없이 나타남.

## 4. 변경 내용

- `sample_order/monitoring.py`: `MonitoringService`(order_status_counts/
  rejected_count/inventory_status), `InventoryStatus`

## 5. 검증 결과

- Test Verify: `pytest -q` → 25 passed. 추가로 REJECTED만 있는 경우, 재고0+미출고
  있는 경우, 주문 한 번도 없는 시료 세 가지를 독립적으로 재현해 확인. PASS
- Compliance Verify: plan 문서 요구사항 5항목 모두 Satisfied(코드 line 단위 근거
  포함). PASS

## 6. 영향 범위

Phase 9(콘솔 UI)가 이 서비스의 반환값을 그대로 화면에 렌더링한다.

## 7. 제약/후속

- 콘솔 출력(색상 배지, 페이지네이션)은 Phase 9에서 다룬다. 이번 Phase는 순수
  데이터 구조까지만 만든다.

## 8. Lessons

이번엔 `doc-consistency-verifier`가 실제로 경계값 문제(재고0+미출고0에서 여유/고갈
동시 만족)를 잡아냈다 — 세션 재시작 이후 진짜 서브에이전트로 전환하자마자 바로
가치를 증명한 사례다. 앞으로도 Phase 착수 전 문서 검증을 형식적으로 넘기지 않는
것이 중요하다.
