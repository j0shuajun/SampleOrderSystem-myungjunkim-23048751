# Phase 1: 시료 모델과 시료 관리 — 결과

Written at (KST): 2026-07-15 12:45

## 1. 한눈에 보는 요약

시료(Sample) 등록·조회·검색 기능을 도메인 계층에 구현했다. 중복 ID 등록은 막는다.
콘솔 입출력과 완전히 분리되어 있다.

## 2. 왜 필요했는지

시스템의 가장 기본 단위인 시료가 없으면 주문(다음 Phase)이 성립하지 않는다. "등록된
시료만 주문 가능하다"는 SPEC.md 규칙을 지키려면, 주문 로직보다 먼저 "시료가 등록돼
있는지 확인하는" 기능이 있어야 한다.

## 3. 예시로 보는 결과

Before: 시료라는 개념 자체가 코드에 없었다.
After:

```python
service = SampleService()
service.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
service.search("웨이퍼")  # -> [Sample(sample_id="S-001", ...)]
service.register(Sample("S-001", ...))  # -> DuplicateSampleError
```

## 4. 변경 내용

- `sample_order/domain.py`: `Sample` 데이터클래스(sample_id/name/
  average_production_time/yield_rate/stock)
- `sample_order/services.py`: `SampleService`(register/list_all/search),
  `DuplicateSampleError`
- `tests/test_sample_order_domain.py`, `tests/test_sample_order_services.py`

## 5. 검증 결과

- Test Verify: `PYTHONPATH=. pytest -q` → 5 passed. PRD/PLAN 대표 시나리오(등록 후
  조회, 이름 검색, 중복 ID 거부) 모두 재현. PASS
- Compliance Verify: PLAN.md Phase 1 요구사항 4항목 모두 Satisfied
  (Sample 필드, register/list_all/search, 중복 ID 거부, 도메인에 print/input 없음). PASS

## 6. 영향 범위

이후 주문(Phase 2~)이 이 `SampleService`를 참조해 존재하는 시료인지 확인한다.

## 7. 제약/후속

- 이번 Phase는 메모리 저장만 한다. 영속성은 Phase 8에서 repository로 연결한다.
- `S-XXX` ID 형식 검증은 강제하지 않았다(Phase 9 콘솔 UI에서 사용자 안내로 처리 예정).

## 8. Lessons

특이사항 없음 — PLAN.md의 대표 테스트 3개가 그대로 구현 체크리스트 역할을 해서
모호함이 없었다.
