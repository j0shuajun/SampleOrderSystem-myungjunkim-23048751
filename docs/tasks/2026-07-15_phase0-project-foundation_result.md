# Phase 0: 프로젝트 기반 — 결과

Written at (KST): 2026-07-15 12:20

## 1. 한눈에 보는 요약

`sample_order` 패키지 골격, 테스트 인프라, 의존성 파일, README 실행 안내를 갖췄다.
이후 Phase들이 이 위에서 도메인 로직을 채워나간다.

## 2. 왜 필요했는지

이후 모든 Phase(시료/주문/생산/영속성/콘솔)는 실행 가능한 Python 패키지와 테스트
러너가 이미 있다고 가정하고 진행된다. 이 골격이 없으면 Phase 1부터 매번 "어떤
디렉토리에 무엇을 두는지"를 새로 정해야 해서 일관성이 깨진다.

## 3. 예시로 보는 결과

Before: 저장소를 새로 clone하면 문서만 있고 실행할 코드가 없었다.
After: 아래 두 줄만 실행하면 테스트가 통과하는 상태가 된다.

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=. ./.venv/bin/pytest -q
# -> 1 passed
```

## 4. 변경 내용

- `sample_order/__init__.py` — 패키지 마커
- `tests/test_sample_order_smoke.py` — 패키지 import 여부를 확인하는 smoke test
- `requirements.txt`(`rich`), `requirements-dev.txt`(`pytest`)
- `README.md`에 가상환경 설치 및 `PYTHONPATH=. pytest -q` 실행 안내 추가
- `.gitignore` 추가 (`__pycache__/`, `.venv/`, `*.pyc`, `.pytest_cache/`)

## 5. 검증 결과

- Test Verify: `PYTHONPATH=. pytest -q` → 1 passed. PASS
- Compliance Verify: PLAN.md Phase 0 체크리스트 6항목 모두 Satisfied. PASS

## 6. 영향 범위

이후 모든 Phase(도메인 모델, 저장소, 생산 큐, 콘솔 UI 등)가 이 골격 위에서 진행된다.
사용자에게 보이는 기능 변화는 없다(순수 기반 작업).

## 7. 제약/후속

- 다음 Phase(시료 모델과 시료 관리)부터 실제 도메인 로직 TDD가 시작된다.

## 8. Lessons

특이사항 없음 — 순수 기반 작업이라 문서/요구사항 해석 이슈가 없었다.
