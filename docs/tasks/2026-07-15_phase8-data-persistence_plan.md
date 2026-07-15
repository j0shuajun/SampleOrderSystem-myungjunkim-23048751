Written at (KST): 2026-07-15 14:20

# Phase 8 — 데이터 영속성 (Data Persistence) Plan

## 1. 목적

현재 `SampleService`/`OrderService`/`ProductionLine`은 모두 파이썬 프로세스가 살아있는
동안만 메모리(`list`)에 데이터를 들고 있다. 프로그램을 껐다 켜면 등록한 시료, 접수한
주문, 진행 중이던 생산 작업이 모두 사라진다.

PRD 4장은 "저장소를 통해 프로그램 재실행 후에도 업무 상태를 유지한다"를 핵심 사용자
가치로 명시하고, SPEC 9장은 시료/주문/생산 작업(그리고 재고는 시료 레코드의 `stock`
필드로서)을 JSON 파일에 저장하도록 요구한다. 이번 Phase는 이 요구를 만족시키는
저장/복원 계층을 추가해, 다음 실행에서도 이전 상태 그대로 이어서 작업할 수 있게 한다.

## 2. 현재 상태

- `sample_order/domain.py`: `Sample`, `Order`, `ProductionJob` dataclass만 정의.
- `sample_order/services.py`: `SampleService._samples`, `OrderService._orders`는
  생성자에서 빈 리스트로 시작하고, 외부에서 통째로 주입/추출할 방법이 없다
  (`list_all()`로 복사본 조회만 가능). `OrderService`는 `_daily_sequence` 딕셔너리로
  `ORD-YYYYMMDD-NNNN`의 날짜별 일련번호를 스스로 관리한다.
- `sample_order/production.py`: `ProductionLine._jobs`도 동일하게 비공개 리스트이며,
  `_next_job_number`로 `JOB-NNNN` 일련번호를 스스로 관리한다. 외부에 공개된 조회
  메서드는 `list_queue()`(QUEUED만) 뿐이라 `IN_PROGRESS`/`DONE` 작업은 조회할 수 없다.
- 저장소(`repository.py`), 파일 입출력(`storage.py`), `cli.py`, `main.py`는 아직 없다
  (`ls sample_order/`에 `domain.py`/`services.py`/`production.py`/`monitoring.py`만
  존재).
- 참고 PoC(`DataPersistence-myungjunkim-23048751`)는 dict 형태의 시료 레코드만
  다루는 `storage.py`(파일 없으면 빈 스키마, JSON 파싱 실패 시 `StorageError`)와
  `repository.py`(딕셔너리 CRUD)를 갖고 있다. 이 프로젝트는 dataclass 기반이라
  그대로 복사할 수 없고, 같은 책임을 이 repo 안에서 다시 구현해야 한다
  (CLAUDE.md 3장 PoC 재사용 정책).

## 3. 목표 상태

- `sample_order/storage.py`: 순수 JSON 파일 입출력 함수(`load(path)`/`save(path, data)`).
  파일이 없으면 빈 스키마(`{"samples": [], "orders": [], "production_jobs": []}`)를
  반환하고, JSON 파싱에 실패하면 사람이 이해할 수 있는 메시지의 `StorageError`를
  던진다.
- `sample_order/repository.py`: dataclass ↔ dict 직렬화/역직렬화와, 서비스 3인방
  (`SampleService`, `OrderService`, `ProductionLine`)의 내부 상태를 통째로
  저장하거나 복원하는 `Repository` 클래스.
- `SampleService`/`OrderService`/`ProductionLine`에 각각 작은 "일괄 복원" 메서드
  (`replace_all`)와, `ProductionLine`에는 상태 무관 전체 작업 조회 메서드
  (`list_all`)를 추가한다. 기존 공개 API(`register`, `place_order`, `approve`,
  `enqueue`, `start_next`, `complete_current` 등)의 동작은 전혀 바뀌지 않는다 —
  순수 추가(additive)다.
- 저장 후 새로 만든 서비스 인스턴스에 복원하면, 시료 재고, 주문 상태, 생산 작업
  상태(`started_at` 포함)가 저장 전과 동일하게 재현된다. 파일이 없을 때는 예외 없이
  빈 상태로 시작한다.
- 이번 Phase는 저장소 계층 자체의 정확성만 증명한다. 콘솔 진입 시 자동 로드,
  종료 시 자동 저장, `--data-file` 같은 실행 인자 처리는 `cli.py`/`main.py`가
  생기는 Phase 9에서 연결한다(아직 `cli.py`가 없으므로 이번 Phase에서 연결할 대상이
  없다).

## 4. 대표 시나리오

### 시나리오 1: 저장 후 재실행 시 데이터 복원 (핵심 성공 케이스)

준비 데이터(SPEC 13장 예시 값 사용):

- 시료 `S-001` "Logic Sample", `average_production_time=5`, `yield_rate=0.9`,
  `stock=3`.
- 주문 `ORD-20260416-0001`, `sample_id=S-001`, `customer_name="Fabless A"`,
  `quantity=10`, 승인 결과 재고 부족으로 `status="PRODUCING"`.
- 생산 작업 `JOB-0001`, `order_id=ORD-20260416-0001`, `shortage=7`,
  `planned_quantity=8`, `status="QUEUED"`, `started_at=None`.

흐름:

1. `SampleService`/`OrderService`/`ProductionLine` 인스턴스를 만들고 위 데이터를
   실제 서비스 메서드(`register`/`place_order`/`approve`)로 채운다.
2. `Repository(path=tmp_path/"data.json").save(sample_service, order_service,
   production_line)`를 호출한다.
3. 파일 내용을 확인하면 SPEC 13장과 동일한 구조의 JSON이 나온다.
4. **새로운** 빈 `SampleService`/`OrderService`/`ProductionLine`을 만들고
   `Repository(path=같은 경로).load_into(sample_service2, order_service2,
   production_line2)`를 호출한다.
5. `sample_service2.find("S-001").stock == 3`, `order_service2.list_all()`에
   `ORD-20260416-0001`(status=`PRODUCING`)이 있고, `production_line2.list_all()`에
   `JOB-0001`(status=`QUEUED`, `started_at is None`)이 있음을 확인한다.

### 시나리오 2: `started_at`이 있는 진행 중 작업도 복원된다

1. 시나리오 1 상태에서 `production_line.start_next(now=lambda:
   datetime(2026, 7, 15, 9, 0, 0))`을 호출해 `JOB-0001`을
   `IN_PROGRESS`, `started_at=datetime(2026,7,15,9,0,0)`으로 만든다.
2. 저장하면 JSON에는 `"started_at": "2026-07-15T09:00:00"`으로 기록된다(SPEC 13장
   말미 예시와 동일한 포맷).
3. 새 인스턴스로 복원하면 `job.started_at == datetime(2026, 7, 15, 9, 0, 0)`
   (문자열이 아니라 실제 `datetime` 객체)로 복원된다.

### 시나리오 3: 파일이 없으면 빈 저장소로 시작한다

1. 존재하지 않는 경로(`tmp_path / "missing.json"`)로 `Repository`를 만든다.
2. 빈 `SampleService`/`OrderService`/`ProductionLine`에 `load_into()`를 호출해도
   예외가 나지 않고, 세 서비스 모두 `list_all()`이 빈 리스트를 반환한다.

### 시나리오 4: 복원 후에도 ID 일련번호가 이어진다

1. 시나리오 1처럼 `ORD-20260416-0001`, `JOB-0001`을 저장했다가 새 인스턴스로
   복원한다.
2. 복원된 `order_service2`에 같은 날짜(`now`가 2026-04-16을 가리키는 상태)로
   새 주문을 접수하면 `ORD-20260416-0002`가 나와야 한다(0001과 충돌하지 않음).
3. 복원된 `production_line2`에 새 부족분 주문을 `enqueue`하면 `JOB-0002`가
   나와야 한다.
4. 이 시나리오는 "복원 후 저장 전 상태를 그대로 이어받아야 한다"는 요구를
   증명한다 — 단순히 리스트만 복사하고 일련번호 카운터를 0/1로 되돌리면 ID가
   중복될 수 있으므로, 반드시 확인이 필요한 케이스다.

### 시나리오 5: 손상된 JSON 파일은 명확한 오류로 알린다

1. `tmp_path / "broken.json"`에 `"{ not valid json"` 같은 깨진 내용을 직접 써 둔다.
2. `storage.load(path)`를 호출하면 `StorageError`가 발생하고, 메시지에 파일 경로가
   포함되어 사람이 원인을 바로 알 수 있다.

## 5. 접근 방식

1. **`sample_order/storage.py` (신규)**
   - `EMPTY_DATA = {"samples": [], "orders": [], "production_jobs": []}`.
   - `load(path)`: 파일 없으면 `EMPTY_DATA`의 얕은 복사본 반환. 있으면 JSON 파싱,
     실패 시 `StorageError`. 파싱 성공 시 누락된 최상위 키는 빈 리스트로 보정.
   - `save(path, data)`: `ensure_ascii=False, indent=2`로 파일에 기록.
   - PoC `storage.py`와 책임은 같지만, 이 저장소 안에서 독립적으로 새로 작성한다
     (import 의존 없음).

2. **`sample_order/domain.py`에 소규모 추가**
   - dataclass 자체는 바꾸지 않는다. 직렬화/역직렬화는 `repository.py`에 둔다
     (도메인 모듈이 JSON 포맷을 몰라도 되게 하기 위해).

3. **`sample_order/services.py`에 추가**
   - `SampleService.replace_all(samples: list[Sample])`: 내부 리스트를 통째로
     교체한다(복원 전용, 중복 검사 없음 — 저장된 데이터는 이미 검증된 것으로
     간주).
   - `OrderService.replace_all(orders: list[Order])`: 내부 리스트를 교체하고,
     각 `order_id`(`ORD-YYYYMMDD-NNNN`)에서 날짜와 일련번호를 파싱해
     `_daily_sequence`를 다시 계산한다(같은 날짜 중 최댓값 + 향후 대비).
   - 기존 `register`/`place_order`/`approve`/`reject`/`release`/`mark_confirmed`는
     수정하지 않는다.

4. **`sample_order/production.py`에 추가**
   - `ProductionLine.list_all()`: 상태와 무관하게 전체 작업 리스트 반환(저장용).
   - `ProductionLine.replace_all(jobs: list[ProductionJob])`: 내부 리스트를
     교체하고, `JOB-NNNN`에서 일련번호를 파싱해 `_next_job_number`를
     `max(기존 번호) + 1`로 재계산한다(작업이 없으면 1 유지).
   - 기존 `enqueue`/`list_queue`/`start_next`/`complete_current`는 수정하지 않는다.

5. **`sample_order/repository.py` (신규)**
   - `_sample_to_dict`/`_order_to_dict`/`_job_to_dict`와 그 역함수. `ProductionJob`만
     `started_at`을 `datetime` ↔ ISO 8601 문자열/`None`으로 변환하는 별도 처리가
     필요하다(다른 필드는 `dataclasses.asdict`로 충분).
   - `Repository` 클래스:
     - `__init__(self, path="data.json")` — 기본 파일명은 SPEC 9장 그대로 `data.json`,
       경로는 생성자 인자로 바꿀 수 있게 해 "실행 시 지정 가능" 요구를 저장소
       계층에서부터 충족한다(실제 CLI 인자 연결은 Phase 9).
     - `save(sample_service, order_service, production_line)` — 세 서비스의
       `list_all()`을 dict로 직렬화해 `storage.save`.
     - `load_into(sample_service, order_service, production_line)` — `storage.load`
       결과를 dataclass 리스트로 역직렬화한 뒤 각 서비스의 `replace_all`을 호출.

6. **테스트 파일**
   - `tests/test_sample_order_storage.py`: `storage.load`/`storage.save`의
     파일없음/정상/손상 케이스.
   - `tests/test_sample_order_repository.py`: 시나리오 1~5를 그대로 옮긴 테스트.
   - 기존 `tests/test_sample_order_services.py`, `test_sample_order_production.py`에는
     `replace_all`/`list_all` 관련 단위 테스트를 추가할 수 있으나, 저장소 통합
     시나리오는 `test_sample_order_repository.py`에 둔다(중복 회피).

## 6. 가정/리스크/트레이드오프

- **가정 1 — `replace_all`은 신뢰된 데이터만 받는다.** 파일에서 읽은 데이터는 이전에
  같은 시스템이 검증해 저장한 것이라고 가정하고, `register`처럼 중복 ID 검사를
  다시 하지 않는다. 만약 사람이 `data.json`을 손으로 편집해 중복 ID를 넣으면
  이번 Phase 범위에서는 검증하지 않는다(스펙에 명시된 요구가 아니므로 과잉 구현을
  피한다).
- **가정 2 — 일련번호 복원은 ID 문자열 파싱으로 한다.** 별도의 "다음 번호"
  필드를 JSON에 추가로 저장하지 않고(스펙 13장 예시와 다른 스키마를 만들지
  않기 위해), 복원 시 기존 ID들에서 역산한다. 트레이드오프: ID 포맷이 바뀌면
  이 파싱 로직도 같이 바뀌어야 한다 — 다만 ID 포맷(SPEC 12장)은 이미 고정된
  결정이므로 리스크는 낮다.
- **가정 3 — Phase 8은 서비스 계층까지만 다루고 CLI 자동 저장/로드는 다루지
  않는다.** `cli.py`가 아직 없으므로 "종료 시 저장, 시작 시 로드"는 연결할 대상이
  없다. PLAN.md도 Phase 8의 대표 테스트를 "저장 후 다시 불러오면 복원된다"로만
  한정하고 있어 이 범위 판단이 타당하다고 본다. Phase 9에서 `main.py`/`cli.py`가
  `Repository`를 실제로 호출하게 된다.
- **트레이드오프 — dict 대신 dataclass를 저장 형태의 진실로 유지.** PoC는 dict를
  그대로 다뤘지만, 이 프로젝트는 이미 dataclass 기반 서비스가 구축되어 있으므로
  repository가 dataclass ↔ dict 변환 책임을 지는 편이 서비스 계층을 다시 설계하는
  것보다 변경 범위가 훨씬 작다. "가장 작은 변경"을 우선한다는 지시에 부합한다.
- **리스크 — 여러 프로세스 동시 접근은 다루지 않는다.** PRD 6장에서 실시간
  멀티프로세스 동시 처리를 명시적으로 제외했으므로, 파일 잠금(lock)이나 동시 쓰기
  충돌 처리는 구현하지 않는다.

## 7. 검증 방법

- TDD로 진행한다: `tests/test_sample_order_storage.py`,
  `tests/test_sample_order_repository.py`에 시나리오 1~5를 실패하는 테스트로 먼저
  작성하고, 실패를 확인한 뒤 최소 구현으로 통과시킨다.
- 구현 완료 후 `PYTHONPATH=. pytest -q`로 전체 스위트를 실행해 회귀가 없는지
  확인한다(기존 `test_sample_order_services.py`/`test_sample_order_production.py`
  등도 함께 통과해야 한다).
- 수동 확인: 임시 디렉터리에서 `Repository.save()`가 만든 JSON 파일을 직접 열어
  SPEC 13장 예시와 동일한 키/값 구조(`samples`/`orders`/`production_jobs`,
  `started_at`이 문자열 또는 `null`)인지 눈으로 대조한다.
