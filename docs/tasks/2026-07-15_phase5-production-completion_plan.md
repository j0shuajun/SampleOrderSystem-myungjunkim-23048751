# Phase 5: 생산 완료 — 계획

Written at (KST): 2026-07-15 16:00

## 1. 목적

생산 큐에 쌓인 작업을 실제로 "시작"하고, 총생산시간만큼 시간이 지난 뒤에만
"완료" 처리할 수 있어야 한다. 완료되면 재고가 늘고 연결된 주문이 `CONFIRMED`가
된다.

## 2. 현재 상태

`ProductionLine.enqueue()`로 작업이 큐에 쌓이기만 하고, 시작/완료 개념이 없다.
`started_at`은 항상 `None`이다.

## 3. 목표 상태

- `ProductionLine.start_next(now)`: 큐 맨 앞의 `QUEUED` 작업을 꺼내 `started_at =
  now()`, 상태를 `IN_PROGRESS`로 바꾼다. 이미 `IN_PROGRESS`인 작업이 있으면 실패
  (단일 라인이므로 동시에 두 작업을 진행하지 않는다).
- `ProductionLine.complete_current(now, sample_service, order_service)`:
  1. 현재 `IN_PROGRESS` 작업이 없으면 실패.
  2. `elapsed = now() - job.started_at`, `total_time = sample.average_production_time
     * job.planned_quantity`.
  3. `elapsed < total_time`이면 `ProductionNotYetCompleteError`(남은 시간 포함)를
     던지고 아무것도 바꾸지 않는다.
  4. 조건을 만족하면 `produced_good_units = floor(job.planned_quantity *
     sample.yield_rate)`만�큼 `sample.stock`을 늘리고, 연결된 주문을 `CONFIRMED`로,
     작업 상태를 `DONE`으로 바꾼다.

## 4. 예시로 이해하기

시료 `S-003`(평균생산시간 0.8분, 수율 0.92)에 계획생산량 142인 작업이 있다고
하자. 총생산시간 = `0.8 * 142 = 113.6`분.

**너무 이른 완료 시도**: 작업 시작 09:00, 완료 시도 10:00(60분 경과, 아직
113.6분 안 지남) → `ProductionNotYetCompleteError("53.6분 남음")`, 아무것도
바뀌지 않음.

**정상 완료**: 작업 시작 09:00, 완료 시도 11:00(120분 경과, 113.6분 넘음) →
`produced_good_units = floor(142 * 0.92) = floor(130.64) = 130`만큼 재고 증가,
연결 주문 `CONFIRMED`, 작업 `DONE`.

## 5. 접근 방식

1. `tests/test_sample_order_production.py`에 시나리오 3개 추가: 너무 이른 완료
   거부, 정상 완료(재고 증가 + 주문 CONFIRMED), 이미 진행 중인 작업이 있을 때
   `start_next` 재호출 실패.
2. `sample_order/production.py`에 `start_next`, `complete_current`,
   `ProductionNotYetCompleteError` 추가. `now` 인자는 `datetime.now`를 기본값으로
   하는 콜러블로 받는다(Phase 2의 `OrderService`와 같은 패턴).
3. `complete_current`가 주문 상태를 바꾸려면 `order_service`(또는 주문 목록)에
   접근해야 한다 — `OrderService`에 `order_id`로 주문을 찾아 상태를 바꾸는 메서드
   (`_find_order`는 이미 있으니 이를 활용하는 공개 메서드, 예: `mark_confirmed`)를
   추가하거나, `ProductionLine`이 주문 리스트를 직접 조작하지 않도록 콜백/서비스
   참조를 받는 구조로 최소화한다.

## 6. 가정/리스크/트레이드오프

- 시간 계산은 `datetime` 뺄셈으로 얻는 `timedelta`를 분(minute) 단위로 변환해
  비교한다(`average_production_time`의 단위가 "분"이므로).
- 단일 라인이므로 `IN_PROGRESS` 작업은 항상 최대 1개다. 이 불변을 테스트로
  확인한다.
- 완료된 작업은 큐(`list_queue`)에서 더 이상 대기 중으로 보이지 않아야 한다 —
  `list_queue()`는 `QUEUED` 상태만 반환하도록 정의한다(진행 중/완료 작업은 별도
  조회 메서드로 분리).

## 7. 검증 방법

- 총생산시간 전 완료 시도 → 예외 발생, 재고/주문 상태 불변.
- 총생산시간 후 완료 → 재고가 `floor(planned_quantity * yield_rate)`만큼 증가,
  주문이 `CONFIRMED`.
- 이미 `IN_PROGRESS`인 작업이 있을 때 `start_next` 재호출 → 실패.
