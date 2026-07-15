# Phase 0: 프로젝트 기반 — 계획

Written at (KST): 2026-07-15 12:00

## 1. 목적

이번 Phase는 기능 구현이 아니라, 이후 모든 Phase가 의존할 실행/테스트 환경과
디렉토리 골격을 만드는 것이 목적이다. `docs/PLAN.md` 2장에 정의된 구조를 그대로
따른다.

## 2. 현재 상태

저장소에는 `CLAUDE.md`, `README.md`, `docs/` 문서만 있고 실제 Python 패키지·테스트
디렉토리·의존성 파일이 전혀 없다.

## 3. 목표 상태

- `sample_order/` 패키지(빈 모듈 껍데기)와 `tests/` 디렉토리가 존재한다.
- `requirements.txt`(`rich`)와 `requirements-dev.txt`(`pytest`)가 있다.
- `PYTHONPATH=. pytest -q`로 실행되는 smoke test 하나가 통과한다.
- `README.md`에 가상환경 설치·테스트 실행 방법이 적혀 있다.

## 4. 대표 시나리오

- 저장소를 새로 clone한 사람이 README만 보고 `pip install -r requirements.txt -r
  requirements-dev.txt` 후 `PYTHONPATH=. pytest -q`를 실행하면 smoke test 1개가
  통과한다.

## 5. 접근 방식

1. `sample_order/__init__.py` 생성(빈 패키지 마커).
2. `tests/test_sample_order_smoke.py`에 `sample_order` 패키지를 import할 수 있는지
   확인하는 최소 테스트 1개 작성.
3. `requirements.txt`, `requirements-dev.txt` 작성.
4. `README.md`에 설치/실행 명령 추가.
5. `.gitignore`에 `__pycache__/`, `.venv/`, `*.pyc` 추가.

## 6. 가정/리스크

- 이번 Phase는 비즈니스 로직이 없으므로 TDD의 "실패하는 테스트"는 단순히
  "패키지가 아직 없어 import가 실패한다"는 형태의 smoke test로 대체한다. SPEC.md와
  충돌하지 않는다.

## 7. 검증 방법

- `PYTHONPATH=. pytest -q` 실행 결과 1 passed.
