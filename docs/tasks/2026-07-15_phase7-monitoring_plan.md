# Phase 7: 모니터링 — 계획

Written at (KST): 2026-07-15 18:00

## 1. 목적

운영 담당자가 "지금 어떤 주문이 몇 건씩 어느 상태에 있는지"와 "어떤 시료가 재고
부족/고갈 위험에 있는지"를 한눈에 확인할 수 있어야 한다(PRD 3장 "운영 담당자"
관심사, 4장 "거절된 주문은 정상 운영 지표에서 제외"). 지금까지 구현한 `SampleService`
/`OrderService`/`ProductionLine`은 각자의 상태 전이만 책임지고, 여러 주문·시료를
가로질러 집계하는 기능은 없다. 이번 Phase는 그 집계를 읽기 전용으로 제공하는
`monitoring.py`를 추가한다.

## 2. 현재 상태 (Phase 7 착수 전)

- `OrderService.list_all()`로 전체 주문 목록은 얻을 수 있지만, 상태별 개수를 세거나
  `REJECTED`를 제외하는 로직은 어디에도 없다.
- `SampleService.list_all()`로 시료 목록과 raw `stock`은 얻을 수 있지만, "미출고
  주문 수량 대비 재고가 충분한지"를 판정하는 로직이 없다.
- SPEC.md 8장에서 "미출고 주문 수량"과 "고갈/여유/부족" 판정 순서, 그리고 재고 0 +
  미출고 0인 경계 케이스(고갈이 최우선)가 이미 명확히 정의되어 있다(doc-consistency
  검증 통과 근거).

## 3. 목표 상태 (Phase 7 완료 시)

새 모듈 `sample_order/monitoring.py`에 읽기 전용 `MonitoringService`를 추가한다.
이 서비스는 기존 `SampleService`/`OrderService` 인스턴스를 참조만 하고, 두 서비스의
상태를 변경하지 않는다(생성/승인/거절/생산/출고 로직은 그대로 Phase 1~6 서비스가
담당).

제공 기능:

1. **상태별 주문 수 집계** — `RESERVED`/`PRODUCING`/`CONFIRMED`/`RELEASE` 각각의
   건수를 반환한다. `REJECTED`는 정상 집계 딕셔너리에는 포함하지 않고, 참고용으로
   별도 필드(예: 거절 건수)로만 노출한다.
2. **시료별 재고 상태 집계** — 등록된 시료마다 다음을 계산한다.
   - `unshipped_quantity` = 그 시료를 대상으로 하는 `RESERVED`+`PRODUCING`+
     `CONFIRMED` 주문 수량의 합(`RELEASE`/`REJECTED` 제외).
   - 판정(SPEC.md 8장 표, 배타적·우선순위 순서):
     1) `stock == 0` → "고갈" (미출고 수량과 무관하게 최우선)
     2) `stock > 0` and `stock >= unshipped_quantity` → "여유"
     3) `stock > 0` and `stock < unshipped_quantity` → "부족"

## 4. 대표 시나리오 (구체적인 값)

### 시나리오 1: 상태별 집계와 REJECTED 제외

주문 목록이 아래와 같다고 하자(시료는 무엇이든 상관없음).

| order_id | status |
|---|---|
| ORD-20260715-0001 | RESERVED |
| ORD-20260715-0002 | RESERVED |
| ORD-20260715-0003 | PRODUCING |
| ORD-20260715-0004 | CONFIRMED |
| ORD-20260715-0005 | RELEASE |
| ORD-20260715-0006 | REJECTED |

`MonitoringService.order_status_counts()` 호출 결과:

```text
{"RESERVED": 2, "PRODUCING": 1, "CONFIRMED": 1, "RELEASE": 1}
```

`REJECTED` 1건은 이 딕셔너리에 나타나지 않는다(정상 집계 총합 = 5, 전체 주문 6건과는
다름). `REJECTED` 건수를 보고 싶으면 별도 메서드(예: `rejected_count()` → `1`)로만
확인한다.

### 시나리오 2: 시료별 재고 상태 — 여유/부족/고갈 세 가지

시료 3개, 각각 다음 주문을 가진다고 하자.

- `S-001` (stock=20): RESERVED 5개, PRODUCING 10개, CONFIRMED 3개, RELEASE 7개
  (RELEASE는 이미 나갔으므로 미출고 수량 계산에서 제외)
  - `unshipped_quantity = 5 + 10 + 3 = 18`
  - `stock(20) >= 18` → **여유**
- `S-002` (stock=5): RESERVED 3개, PRODUCING 5개 (`unshipped_quantity = 8`)
  - `stock(5) > 0`이고 `5 < 8` → **부족**
- `S-003` (stock=0): 주문 없음(`unshipped_quantity = 0`)
  - `stock == 0` → **고갈** (미출고 수요가 0이어도 재고가 물리적으로 없으므로
    "부족" 계산을 거치지 않고 곧바로 고갈로 판정 — SPEC.md 8장의 경계 케이스 예시와
    동일한 상황)

`MonitoringService.inventory_status()`는 이 세 시료에 대해 각각
`(sample_id, name, stock, unshipped_quantity, state)` 형태의 결과를 리스트로
반환한다.

## 5. 접근 방식

1. `tests/test_sample_order_monitoring.py`를 새로 만든다(테스트 파일 네이밍 규칙:
   대상 모듈 `sample_order/monitoring.py` → `tests/test_sample_order_monitoring.py`).
   시나리오 1(상태별 집계, REJECTED 제외)과 시나리오 2(여유/부족/고갈, 특히 재고 0 +
   미출고 0 경계 케이스)를 각각 실패하는 테스트로 먼저 작성한다.
2. `sample_order/monitoring.py`를 새로 만든다.
   - `InventoryStatus` 같은 결과용 데이터 구조(예: `dataclass`)를 정의해 호출부가
     `sample_id`/`name`/`stock`/`unshipped_quantity`/`state` 필드로 바로 접근하게
     한다.
   - `MonitoringService(sample_service, order_service)`:
     - `order_status_counts()` — RESERVED/PRODUCING/CONFIRMED/RELEASE 4개 키를
       가진 dict 반환(0건이어도 키는 항상 존재).
     - `rejected_count()` — REJECTED 건수만 별도 반환.
     - `inventory_status()` — 등록된 시료 전체에 대해 `InventoryStatus` 리스트 반환.
   - `print`/`input` 등 콘솔 I/O는 두지 않는다(추후 Phase 9에서 `cli.py`가 이 결과를
     받아 렌더링).
3. 두 서비스의 기존 공개 메서드(`list_all()` 등)만 사용하고, 내부 `_orders`/
   `_samples` 리스트에 직접 접근하지 않는다(캡슐화 유지, 기존 서비스 코드는 변경하지
   않는다).

## 6. 가정/리스크/트레이드오프

- **REJECTED 노출 방식**: SPEC.md는 "REJECTED는 별도 참고 정보로 표시할 수 있지만
  정상 집계에서는 제외한다"고만 하고 구체적인 API 형태는 정하지 않았다. 이번 Phase는
  `order_status_counts()`의 반환 딕셔너리에는 아예 키를 넣지 않고, 원하면 참고할 수
  있도록 `rejected_count()`를 별도로 둔다(딕셔너리 안에 넣고 "집계에는 합산하지
  않는다"는 식의 설계도 가능했으나, 실수로 합계에 섞여 들어갈 위험을 없애기 위해
  아예 분리했다).
- **집계 범위**: `inventory_status()`는 등록된 시료 전체를 대상으로 한다(주문이
  하나도 없는 시료도 포함). SPEC.md 8장의 경계 케이스 예시(재고 0, 미출고 0 → 고갈)가
  바로 이런 시료를 가리키므로, 등록된 시료를 빠짐없이 순회해야 그 경계 케이스를
  검증할 수 있다.
- **Phase 범위**: 콘솔 출력(색상 배지, 페이지네이션 등 SPEC.md 11장)은 Phase 9의
  몫이다. 이번 Phase는 `monitoring.py`가 반환하는 순수 데이터 구조까지만 만들고,
  렌더링은 하지 않는다.

## 7. 검증 방법

- `PYTHONPATH=. pytest -q`로 `tests/test_sample_order_monitoring.py`의 두 시나리오
  (상태별 집계 + REJECTED 제외, 여유/부족/고갈 3분류 + 재고 0·미출고 0 경계 케이스)가
  모두 통과하는지 확인한다.
- 기존 테스트(`test_sample_order_domain.py`/`services.py`/`production.py`)가 이번
  변경으로 깨지지 않았는지 전체 테스트 실행으로 확인한다.
- `monitoring.py`에 `print`/`input`이 없는지, 두 서비스의 상태를 변경하는 코드가
  없는지(읽기 전용) 코드 리뷰로 확인한다.
