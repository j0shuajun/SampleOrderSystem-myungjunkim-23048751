# Phase 10: 최종 감사 후속 조치 — 결과

Written at (KST): 2026-07-15 21:30

## 1. 한눈에 보는 요약

전체 프로젝트 최종 감사에서 나온 3개 지적사항(입력값 검증 부재, 약속했던 ID
힌트 누락, PRD 범위였던 seed 데이터 미구현)을 모두 반영했다.

## 2. 왜 필요했는지

수율 0, 음수 생산시간/수량 같은 극단값을 입력하면 프로그램이 죽을 수 있었고,
PRD가 약속한 seed 데이터 기능이 빠져 있었다. 최종 감사(compliance-verifier)가
아니었다면 놓칠 뻔한 항목들이다.

## 3. 예시로 보는 결과

- 수율에 `0` 입력 → `오류: 수율은 0보다 크고 1 이하이어야 합니다: 0.0`, 메뉴로 복귀(안 죽음)
- 수율 `1.0`(상한 경계) → 정상 등록됨
- 주문 수량 `-3` → `오류: 주문 수량은 1 이상이어야 합니다: -3`
- 시료 등록 시 `시료 ID (예: S-001) > ` 힌트 표시
- `python -m sample_order.seed demo.json --samples 5 --orders 20 --seed 99`를 두 번 실행하면 완전히 동일한 파일이 생성됨(재현성 확인), `main.py`로 바로 열림

## 4. 변경 내용

- `sample_order/services.py`: `InvalidSampleError`, `InvalidOrderQuantityError`,
  `_validate_sample`, `place_order`의 수량 검증
- `sample_order/cli.py`: 새 예외 처리 연결, 시료 ID 프롬프트에 힌트 추가
- `sample_order/seed.py`(신규): DummyDataGenerator PoC를 참고해 재구현한 더미
  데이터 생성기 (`python -m sample_order.seed`로만 실행, 자동 적재 없음)
- `README.md`에 seed 실행법 추가, `docs/SPEC.md`의 "예상 생산 시간" 필드 불일치
  수정(저장하지 않고 계산으로 명시)

## 5. 검증 결과

- Test Verify: `pytest -q` → 52 passed. 추가로 `main.py`를 직접 구동해 검증
  메시지 4종·경계값·seed 재현성(diff 동일)·참조무결성(잘못된 sample_id/job
  참조 0건)까지 전부 실제로 확인. PASS
- Compliance Verify: plan 문서 요구사항 7항목 모두 Satisfied(line 단위 근거).
  seed.py가 main.py/cli.py 어디에서도 호출되지 않음(자동 적재 없음)을 grep으로
  재확인. PASS

## 6. 영향 범위

기존 Phase 0~9의 어떤 공개 동작도 바뀌지 않았다(순수 추가). 이제 시료
등록·주문 접수 시 잘못된 값을 넣어도 프로그램이 죽지 않고, PRD가 요구한 seed
데이터 기능도 사용할 수 있다.

## 7. 제약/후속

- `seed.py`는 SPEC.md 10장 메뉴 표에 없으므로 콘솔 메뉴에 노출하지 않고 별도
  스크립트로만 유지한다.
- 이름(name) 길이 제한 등 SPEC에 명시되지 않은 추가 검증은 하지 않았다(과잉
  구현 방지).

## 8. Lessons

- 최종(프로젝트 전체) compliance-verifier 감사가 Phase별 감사로는 안 보이던
  "문서가 약속했지만 나중 Phase에서 빠뜨린 것"(ID 힌트)과 "PRD 범위인데
  구현이 안 된 것"(seed.py)을 잡아냈다 — Phase 단위 검증만으로는 충분하지
  않을 수 있으니, 프로젝트 완료 시점에 전체를 한 번 더 훑는 최종 감사가
  유효하다는 걸 확인했다.
- 이번에도 제가 순서(문서→승인→커밋)를 건너뛰고 바로 테스트부터 커밋했다가
  사용자가 바로잡아줬다 — 작은 후속 수정이라고 해서 합의된 흐름을 생략하면
  안 된다는 걸 다시 확인했다.
