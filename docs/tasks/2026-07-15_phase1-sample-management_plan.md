# Phase 1: 시료 모델과 시료 관리 — 계획

Written at (KST): 2026-07-15 12:30

## 1. 목적

시스템의 가장 기본 단위인 시료(Sample)를 등록·조회·검색할 수 있어야 이후 주문/생산
로직이 성립한다. 이번 Phase에서 `sample_order/domain.py`(Sample 모델)와
`sample_order/services.py`(등록/조회/검색 서비스)를 만든다.

## 2. 현재 상태

`sample_order` 패키지가 비어 있다. 시료 개념이 코드에 전혀 없다.

## 3. 목표 상태

- `Sample` 데이터 클래스: `sample_id`, `name`, `average_production_time`,
  `yield_rate`, `stock` (SPEC.md 2장).
- `SampleService`: `register(sample)`, `list_all()`, `search(keyword)`.
- 중복 `sample_id` 등록은 예외로 막는다.
- 콘솔 입출력 없음(도메인 로직만).

## 4. 대표 시나리오 (PLAN.md 대표 테스트 그대로)

- 시료 등록 후 `list_all()`에서 조회된다.
- 이름 일부로 `search()`하면 해당 시료가 나온다.
- 이미 있는 `sample_id`로 재등록하면 실패한다.

## 5. 접근 방식

1. `tests/test_sample_order_domain.py`: `Sample` 생성/필드 확인.
2. `tests/test_sample_order_services.py`: 등록, 목록조회, 이름검색, 중복ID 거부.
3. `sample_order/domain.py`에 `Sample` 정의.
4. `sample_order/services.py`에 `SampleService`(메모리 리스트 기반, 이번 Phase는
   영속성 붙이지 않음 — Phase 8에서 repository와 연결) 정의.

## 6. 가정/리스크

- 이번 Phase의 `SampleService`는 메모리 저장만 한다. 영속성 연결은 Phase 8
  (데이터 영속성)에서 repository로 교체/연결한다. PLAN.md의 우선순위("도메인 로직부터,
  저장은 나중")와 일치한다.
- ID 형식(`S-XXX`) 검증까지는 이번 Phase에서 강제하지 않는다 — 형식 강제는 SPEC.md에
  "형식"이라고만 되어 있고 필수 검증 요구사항으로 명시되지 않았으므로, 등록 시 임의
  문자열 ID도 허용한다. 이후 콘솔 UI(Phase 9)에서 사용자에게 `S-XXX` 형식을
  안내한다.

## 7. 검증 방법

- `PYTHONPATH=. pytest -q tests/test_sample_order_domain.py
  tests/test_sample_order_services.py` 전체 통과.
