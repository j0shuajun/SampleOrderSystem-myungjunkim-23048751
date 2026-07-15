# Phase 2: 주문 접수와 상태 모델 — 계획

Written at (KST): 2026-07-15 13:00

## 1. 목적

고객이 시료를 요청하면 "주문"이라는 기록이 생기고, 이 주문은 반드시 `RESERVED`라는
접수 상태에서 시작해야 한다. 이번 Phase는 그 최초 접수 단계만 다룬다(승인/거절은
Phase 3에서).

## 2. 현재 상태

`Sample`과 `SampleService`만 있고, "주문(Order)"이라는 개념 자체가 코드에 없다.

## 3. 목표 상태

- `Order` 데이터클래스: `order_id`, `sample_id`, `customer_name`, `quantity`,
  `status`.
- `OrderService.place_order(sample_id, customer_name, quantity)`:
  1. `sample_id`가 `SampleService`에 등록돼 있는지 확인 — 없으면 예외.
  2. 있으면 `order_id`를 `ORD-YYYYMMDD-0000` 형식으로 자동 채번하고, `status`를
     `RESERVED`로 만들어 저장한다.
- `OrderService.list_all()`로 접수된 주문을 조회할 수 있다.

## 4. 예시로 이해하기

예를 들어 설명하면 이렇습니다.

**정상 케이스**: 시료 목록에 `S-001`(실리콘 웨이퍼-8인치)이 이미 등록돼 있다고
합시다. 여기서 "삼성전자 파운드리"가 `S-001`을 200개 주문하면,

```
place_order(sample_id="S-001", customer_name="삼성전자 파운드리", quantity=200)
```

이 호출은 아래와 같은 주문 1건을 만듭니다(오늘 날짜가 2026-07-15이고 이게 오늘
첫 번째 주문이라고 가정).

```
Order(
    order_id="ORD-20260715-0001",
    sample_id="S-001",
    customer_name="삼성전자 파운드리",
    quantity=200,
    status="RESERVED",
)
```

**실패 케이스**: 만약 존재하지 않는 `S-999`로 주문을 넣으려 하면(등록된 적 없는
시료이므로),

```
place_order(sample_id="S-999", customer_name="삼성전자 파운드리", quantity=200)
```

이 호출은 주문을 만들지 않고 `UnknownSampleError` 같은 예외를 던집니다 — "없는
시료로는 주문할 수 없다"는 SPEC.md 규칙을 그대로 지키는 것입니다.

## 5. 접근 방식

1. `tests/test_sample_order_domain.py`에 `Order` 필드 확인 테스트 추가.
2. `tests/test_sample_order_services.py`(또는 새 테스트 파일)에 위 두 시나리오
   (정상 접수, 없는 시료 실패) 테스트 추가.
3. `sample_order/domain.py`에 `Order` 추가.
4. `sample_order/services.py`에 `OrderService`, `UnknownSampleError` 추가.
   `OrderService`는 생성자에서 `SampleService` 인스턴스를 받아 시료 존재 여부를
   확인한다.

## 6. 가정/리스크

- 주문 ID의 날짜(YYYYMMDD)는 실제 시스템 시각(`datetime.now()`)을 쓴다. 이후
  생산 완료 판정(Phase 5)에서 도입할 "테스트에서 mocking 가능한 시간 소스"와 같은
  방식(주입 가능한 `now` 콜러블, 기본값 `datetime.now`)을 여기서도 미리 적용해,
  테스트가 실제 시간에 의존하지 않게 한다.
- 하루 안에서의 일련번호(`0001`, `0002`...)는 이번 서비스 인스턴스 안에서만
  증가한다. 여러 프로세스 동시 실행은 범위 밖(PRD 제외 항목)이므로 고려하지 않는다.

## 7. 검증 방법

- 정상 접수 시 `status == "RESERVED"`이고 `order_id`가 `ORD-YYYYMMDD-NNNN` 형식인지
  확인.
- 없는 `sample_id`로 접수 시도 시 예외가 발생하고 주문이 생성되지 않는지 확인.
