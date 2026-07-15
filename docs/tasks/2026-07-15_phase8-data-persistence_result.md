# Phase 8: 데이터 영속성 — 결과

Written at (KST): 2026-07-15 19:00

## 1. 한눈에 보는 요약

시료·주문·생산작업을 JSON 파일로 저장하고, 새 프로세스에서 그대로 복원할 수 있는
`Repository`를 추가했다. 복원 후에도 주문/작업 ID 일련번호가 이어져 충돌하지 않는다.

## 2. 왜 필요했는지

PRD가 핵심 가치로 명시한 "저장소를 통해 프로그램 재실행 후에도 업무 상태를
유지한다"를 실제로 만족시키는 단계다. 지금까지의 서비스들은 프로세스가 살아있는
동안만 메모리에 데이터를 들고 있었다.

## 3. 예시로 보는 결과

SPEC.md 13장 예시 그대로: 시료 `S-001`(재고3)에 10개 주문(`ORD-20260416-0001`)이
재고 부족으로 `PRODUCING`, 생산작업 `JOB-0001`(부족분7, 계획생산량8) 생성 →
저장하면 JSON 파일에 그대로 기록되고, 새 서비스 인스턴스로 복원하면 재고3/주문
상태/작업 상태가 전부 동일하게 돌아온다. 작업을 `IN_PROGRESS`로 만들고
(`started_at` 기록) 저장하면 JSON엔 `"2026-07-15T09:00:00"` 문자열로, 복원하면
다시 진짜 `datetime` 객체로 돌아온다. 복원 후 같은 날짜에 새 주문을 넣으면
`ORD-20260416-0002`(0001과 충돌 없음), 새 생산작업은 `JOB-0002`가 나온다.

## 4. 변경 내용

- `sample_order/storage.py`: 순수 JSON load/save, 파일없음→빈 스키마, 파싱실패→
  `StorageError`(경로 포함 메시지)
- `sample_order/repository.py`: dataclass↔dict 직렬화(`started_at`은 ISO 8601
  문자열/`null`), `Repository.save`/`load_into`
- `sample_order/services.py`: `SampleService.replace_all`,
  `OrderService.replace_all`(ID에서 일련번호 역산)
- `sample_order/production.py`: `ProductionLine.list_all`, `replace_all`(ID에서
  작업번호 역산)
- 기존 공개 메서드(register/place_order/approve/reject/release/mark_confirmed/
  enqueue/list_queue/start_next/complete_current)는 전혀 바뀌지 않음(순수 추가)

## 5. 검증 결과

- Test Verify: `pytest -q` → 34 passed. 추가로 SPEC 13장 예시와 저장된 실제 JSON을
  직접 대조(키 이름, `started_at` 포맷)하고, 복원 후 ID 연속성, 파일없음, 손상된
  JSON까지 독립적으로 재현. PASS
- Compliance Verify: plan 문서 요구사항 10항목 모두 Satisfied(코드 line 단위 근거
  포함, 기존 메서드 미변경도 직접 확인). PASS

## 6. 영향 범위

Phase 9(콘솔 UI)의 `main.py`가 시작 시 `Repository.load_into()`, 종료 시
`Repository.save()`를 호출하게 된다.

## 7. 제약/후속

- 콘솔 시작 시 자동 로드/종료 시 자동 저장, 실행 인자로 파일 경로 지정은
  `cli.py`/`main.py`가 생기는 Phase 9에서 연결한다.
- 여러 프로세스 동시 접근(파일 잠금)은 다루지 않는다(PRD 범위 제외와 일치).

## 8. Lessons

`replace_all`로 리스트를 통째로 교체할 때, 카운터(일련번호)를 단순히 초기화하면
안 되고 기존 ID를 파싱해 역산해야 한다는 게 이번 Phase의 핵심이었다 — plan
문서에서 이 요구를 대표 시나리오로 명시해뒀던 덕분에 구현과 검증 모두 이 부분을
놓치지 않았다. 저장/복원처럼 "상태를 통째로 교체"하는 기능을 추가할 때는 내부에서
스스로 관리하는 파생 상태(카운터 등)가 있는지 항상 점검해야 한다.
