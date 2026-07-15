# Phase 10: 최종 감사 후속 조치 — 계획

Written at (KST): 2026-07-15 21:00

## 1. 목적

전체 프로젝트 최종 감사(compliance-verifier)에서 발견한 3개 항목을 처리한다.

1. SPEC.md 2장이 이미 명시한 필드 제약(수율 0<x≤1 등)이 코드에서 검증되지 않아
   극단값 입력 시 `ZeroDivisionError` 등으로 프로그램이 죽을 수 있다.
2. Phase 1 result 문서가 "콘솔 UI에서 ID 형식을 안내하겠다"고 약속했지만
   Phase 9 구현에서 빠졌다.
3. PRD.md가 범위에 포함한 "더미/seed 데이터 활용"이 아직 구현되지 않았다.

## 2. 현재 상태

- `SampleService.register`/`OrderService.place_order`는 값의 범위를 검증하지
  않는다.
- `cli.py`의 시료 ID 프롬프트는 `"시료 ID > "`로, 형식 힌트가 없다.
- `sample_order/seed.py`가 존재하지 않는다.

## 3. 목표 상태

- `SampleService.register`가 `yield_rate`(0<x≤1), `average_production_time`(>0),
  `stock`(≥0) 범위를 검증하고, 위반 시 `InvalidSampleError`를 던진다.
- `OrderService.place_order`가 `quantity`(≥1)를 검증하고, 위반 시
  `InvalidOrderQuantityError`를 던진다.
- `cli.py`의 시료 ID 입력 라벨이 `"시료 ID (예: S-001) > "`로 바뀐다.
- `sample_order/seed.py`(신규): DummyDataGenerator PoC의 생성 로직을 이 저장소
  dataclass 기반으로 재구현해, 시료/주문/생산작업 더미 데이터를 만들어
  `Repository`로 저장한다. 명시적 명령(별도 스크립트 실행)으로만 동작하고,
  `main.py`/`cli.py`는 건드리지 않는다(자동 적재 금지, CLAUDE.md 4장).

## 4. 예시로 이해하기

**검증 실패 예시**: 시료 등록 시 수율에 `0`을 입력하면 →
`오류: 수율은 0보다 크고 1 이하이어야 합니다: 0`. 시료는 등록되지 않는다.
주문 수량에 `-5`를 입력하면 → `오류: 주문 수량은 1 이상이어야 합니다: -5`.

**ID 힌트 예시**: 시료 관리 메뉴에서 등록 선택 시 `시료 ID (예: S-001) > `로
표시된다(실제 형식 강제는 하지 않음, 안내만).

**seed 예시**: `./.venv/bin/python -m sample_order.seed demo.json --samples 5
--orders 20 --seed 42`를 실행하면, `demo.json`에 시료 5종·주문 20건(5가지 상태
고루 분포)·해당 생산작업이 채워진다. 이후 `python3 main.py demo.json`으로 그
데이터를 그대로 열어볼 수 있다.

## 5. 접근 방식

1. `tests/test_sample_order_services.py`에 검증 시나리오 추가(이미 작성해
   커밋됨: 수율/생산시간/재고/수량 경계값).
2. `sample_order/services.py`에 `InvalidSampleError`, `InvalidOrderQuantityError`
   추가하고 `register`/`place_order`에 검증 로직 삽입.
3. `sample_order/cli.py`의 `_handle_sample_register` 프롬프트 라벨 수정.
4. `sample_order/seed.py` 신규 작성 — DummyDataGenerator PoC의 스키마(`S-XXX`,
   `ORD-YYYYMMDD-NNNN`, 상태 5종 분포)를 참고하되 이 저장소의 dataclass/
   Repository를 사용해 독립적으로 재구현한다(PoC 코드 직접 의존 없음).
5. `tests/test_sample_order_seed.py` 신규: 지정 개수 생성, 같은 seed 재현성,
   생성된 주문의 sample_id 참조 무결성을 확인한다.

## 6. 가정/리스크/트레이드오프

- 검증 범위는 SPEC.md 2장에 이미 명시된 제약만 강제한다(이름 길이 제한 등
  스펙에 없는 임의 검증은 추가하지 않는다 — 과잉 구현 방지).
- ID 힌트는 안내 문구일 뿐 강제 검증이 아니다(사용자가 승인한 방향 그대로).
- `seed.py`는 메뉴(SPEC.md 10장)에 포함되지 않으므로 `cli.py`/`main.py`와는
  독립된 별도 실행 경로(`python -m sample_order.seed`)로 둔다.

## 7. 검증 방법

- `PYTHONPATH=. pytest -q` 전체 통과(기존 39개 + 신규 검증/seed 테스트).
- `python3 main.py`를 실행해 수율 0 입력 시 오류 후 메뉴 복귀, 시료 ID 프롬프트에
  힌트가 보이는지 수동 확인.
- `seed.py` 실행 결과 JSON을 `main.py`로 열어 정상적으로 보이는지 확인.
