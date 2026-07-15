# Phase 4: 생산 큐와 재고 부족 처리 — 계획

Written at (KST): 2026-07-15 15:00

## 1. 목적

Phase 3에서 주문이 `PRODUCING`이 되는 상태 전이는 만들었지만, "실제로 얼마나
생산해야 하는지"를 계산하고 FIFO 큐에 쌓는 로직은 아직 없다. 이번 Phase에서 그
생산 작업(Production Job)을 만든다.

## 2. 현재 상태

`OrderService.approve()`가 가용재고 부족 시 주문 상태를 `PRODUCING`으로만 바꾸고
끝난다. 생산 작업이라는 개념, 큐, 계획 생산량 계산이 코드에 없다.

## 3. 목표 상태

- `sample_order/domain.py`에 `ProductionJob`(job_id, order_id, sample_id, shortage,
  planned_quantity, status, started_at) 추가.
- `sample_order/production.py`에 `ProductionLine`:
  - `enqueue(order, sample, shortage)`: `planned_quantity = ceil(shortage /
    sample.yield_rate)`를 계산해 큐 맨 뒤에 job을 추가.
  - `list_queue()`: 대기 중인 job을 FIFO 순서로 반환.
- `OrderService.approve()`가 `PRODUCING`으로 전환할 때 `ProductionLine.enqueue()`를
  호출하도록 연결(생성자에서 `production_line`을 선택적으로 받는다).

## 4. 예시로 이해하기

시료 `S-003`(SiC 파워기판-6인치, 수율 0.92)의 재고가 70인데 주문이 200개
들어왔다고 하자. 승인 시 가용재고가 70(다른 미출고 주문 없다고 가정)이라 부족분은
`200 - 70 = 130`이다.

```
shortage = 130
planned_quantity = ceil(130 / 0.92) = ceil(141.3) = 142
```

이 주문은 `PRODUCING`이 되고, 생산 큐 맨 뒤에 아래 작업이 추가된다.

```
ProductionJob(
    order_id="ORD-...",
    sample_id="S-003",
    shortage=130,
    planned_quantity=142,
    status="QUEUED",
)
```

다른 주문이 먼저 `PRODUCING`으로 승인돼 있었다면, 그 작업이 큐에서 앞에 있고 이번
작업은 그 뒤에 붙는다(FIFO). `list_queue()`를 호출하면 항상 먼저 들어온 순서대로
나온다.

## 5. 접근 방식

1. `tests/test_sample_order_domain.py`: `ProductionJob` 필드 확인 테스트 추가.
2. `tests/test_sample_order_production.py`(신규, PLAN.md 구조에 이미 정의됨):
   - 부족분/수율로 계획 생산량 계산.
   - 여러 작업을 enqueue했을 때 `list_queue()`가 FIFO 순서로 반환하는지.
3. `tests/test_sample_order_services.py`: 승인 시 `PRODUCING`이 되면 생산 큐에
   job이 하나 생기는지(연동 테스트).
4. `sample_order/domain.py`에 `ProductionJob` 추가.
5. `sample_order/production.py`에 `ProductionLine` 추가.
6. `sample_order/services.py`의 `OrderService`가 `production_line`을 받아 `approve()`
   안에서 연결.

## 6. 가정/리스크/트레이드오프

- `started_at`(작업 시작 시각)은 이번 Phase에서는 큐에 들어갈 때가 아니라, Phase 5
  ("다음 생산 작업 시작" 메뉴 동작)에서 실제로 채워 넣는다. 이번 Phase에서는 필드만
  갖고 있고 `None`으로 둔다 — SPEC.md 6장은 "작업 시작"과 "생산 완료"를 별개
  동작으로 구분하므로, 큐에 쌓이는 시점과 실제 작업이 시작되는 시점을 혼동하지
  않기 위함이다.
- 계획 생산량 계산에서 나눗셈은 `math.ceil`을 쓴다(파이썬 표준 라이브러리).

## 7. 검증 방법

- 부족분 130, 수율 0.92 → 계획 생산량 142인지 확인.
- 3개 작업을 순서대로 enqueue하고 `list_queue()` 순서가 입력 순서와 같은지 확인.
- 승인으로 `PRODUCING`이 된 주문이 큐에도 나타나는지 확인.
