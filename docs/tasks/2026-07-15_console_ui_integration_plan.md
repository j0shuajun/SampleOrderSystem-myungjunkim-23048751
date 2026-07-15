Written at (KST): 2026-07-15 14:30

# Phase 9 — 콘솔 UI 통합 (Plan)

## 1. 목적

Phase 1~8에서 만든 도메인 서비스(`SampleService`/`OrderService`/`ProductionLine`/
`MonitoringService`)와 저장소(`Repository`)는 모두 순수 로직으로만 존재하고, 사람이
직접 실행해서 쓸 수 있는 진입점이 아직 없다. 지금 상태로는 pytest로만 동작을
확인할 수 있고, PRD 7장이 요구하는 "담당자가 콘솔 메뉴만으로 주문 접수부터 출고까지
진행할 수 있다"는 성공 기준을 실제로 만족시키지 못한다.

이번 Phase의 목적은 이 8개 Phase의 도메인 로직을 하나의 콘솔 애플리케이션으로
묶어서, PRD가 정의한 3명의 사용자(주문 담당자/생산 담당자/운영 담당자)가 실제로
메뉴를 눌러가며 SPEC.md 5장의 대표 흐름(재고 충분/부족/거절)을 끝까지 수행하고,
프로그램을 종료했다가 다시 실행해도 그 결과가 남아있는지 확인할 수 있게 만드는
것이다.

## 2. 현재 상태

- `sample_order/domain.py`, `services.py`, `production.py`, `monitoring.py`,
  `repository.py`, `storage.py`가 모두 존재하고 각 모듈 단위 테스트가 통과한다.
- `cli.py`, `main.py`, `seed.py`는 아직 존재하지 않는다(`sample_order/` 안에는
  domain/services/production/monitoring/repository/storage/`__init__.py`만 있다).
- `print`/`input`은 코드베이스 어디에도 없다(도메인이 I/O로부터 완전히 분리된
  상태 그대로 유지되고 있다).
- `requirements.txt`에는 `rich`가, `requirements-dev.txt`에는 `pytest`가 이미
  등록되어 있어 콘솔 렌더링에 바로 쓸 수 있다.
- 저장 데이터를 다루려면 `SampleService`/`OrderService`/`ProductionLine` 인스턴스를
  프로그램이 직접 생성하고, `ProductionLine`을 `OrderService(production_line=...)`에
  주입해야 하며, `Repository.load_into(...)`/`Repository.save(...)`를 호출하는 쪽이
  필요하다 — 지금은 이걸 호출하는 코드가 없다.
- 사람이 실행할 방법이 전혀 없으므로, "시료 등록 → 주문 접수 → 승인 → 생산 →
  출고 → 모니터링 → 재실행 후 복원"이라는 PLAN.md 6장의 최종 수동 시나리오를
  아직 한 번도 手動으로 검증하지 못했다.

## 3. 목표 상태

- `python3 main.py` (또는 `python3 main.py my_data.json`)로 프로그램을 실행하면
  SPEC.md 10장의 6+1 메뉴가 뜨고, 번호를 입력해 시료 관리/시료 주문/주문
  승인·거절/모니터링/생산 라인 조회/출고 처리/종료를 오갈 수 있다.
- 상태 배지(`RESERVED`/`CONFIRMED`/`PRODUCING`/`RELEASE`/`REJECTED`)가 `rich`로
  색이 입혀져 표시되고, 색을 못 보는 환경에서도 라벨 텍스트만으로 의미가 통한다.
- 시료/주문 목록이 한 화면 분량(10건)을 넘으면 전체를 한 번에 쏟아내지 않고
  `...외 N종 [N] 다음페이지` 형태의 페이지네이션을 적용한다.
- 프로그램 시작 시 `Repository.load_into(...)`로 지정된 경로(기본 `data.json`)의
  기존 데이터를 불러오고, "0. 종료"를 선택하면 `Repository.save(...)`로 저장한 뒤
  종료한다. 같은 경로로 재실행하면 방금 만든 시료/주문/생산 작업이 그대로 보인다.
- `cli.py`는 화면 렌더링과 입력 처리만 담당하고, 상태 판단/계산(가용재고, 생산량,
  완료 판정 등)은 전부 기존 서비스 메서드 호출로 위임한다. `domain.py`/
  `services.py`/`production.py`/`monitoring.py`에는 `print`/`input`이 여전히
  등장하지 않는다.

## 4. 대표 시나리오

### 시나리오 1: 첫 실행 — 시료 등록 후 조회

```
$ python3 main.py demo.json
(demo.json 파일이 없으므로 빈 저장소로 시작)

==============================================
 반도체 시료 생산주문관리 시스템
----------------------------------------------
[1] 시료 관리   [2] 시료 주문   [3] 주문 승인/거절
[4] 모니터링    [5] 생산 라인 조회   [6] 출고 처리
[0] 종료
==============================================
선택 > 1

[1] 시료 등록  [2] 시료 목록  [3] 시료 검색  [0] 이전 메뉴
선택 > 1
시료 ID > S-001
이름 > Logic Sample
평균 생산시간(min/ea) > 5
수율(0~1) > 0.9
재고 > 3
등록 완료: S-001 (Logic Sample)

선택 > 2
등록 시료 목록 (총 1종)
  S-001  Logic Sample   재고 3   수율 0.9
```

### 시나리오 2: 재고 부족 주문 → 생산 → 출고 (SPEC.md 흐름 B)

```
선택 > 2 (시료 주문)
시료 ID > S-001
고객명 > Fabless A
수량 > 10
접수 완료: ORD-20260715-0001 [RESERVED]

선택 > 3 (주문 승인/거절)
승인 대기 목록: ORD-20260715-0001 Fabless A S-001 x10 [RESERVED]
주문 ID > ORD-20260715-0001
[1] 승인  [2] 거절 > 1
재고 부족으로 생산 큐에 등록되었습니다. -> ORD-20260715-0001 [PRODUCING]

선택 > 5 (생산 라인 조회)
현재 진행 중: 없음
대기 큐: JOB-0001 (S-001, 부족분 7, 계획 8개)
[1] 다음 작업 시작  [2] 완료 처리  [0] 이전 메뉴 > 1
JOB-0001 작업을 시작했습니다.

(총생산시간 40분 경과 후 재실행 없이 재접속했다고 가정)
선택 > 5
[2] 완료 처리
완료 처리 결과: JOB-0001 DONE, 재고 +7 (planned 8 x yield 0.9 -> floor=7)
ORD-20260715-0001 상태가 CONFIRMED로 바뀌었습니다.

선택 > 6 (출고 처리)
출고 대상: ORD-20260715-0001 Fabless A S-001 x10 [CONFIRMED]
주문 ID > ORD-20260715-0001
출고 완료: ORD-20260715-0001 [RELEASE], 재고 0

선택 > 0
저장 후 종료합니다. (demo.json)
```

### 시나리오 3: 재실행 후 데이터 복원

```
$ python3 main.py demo.json
선택 > 4 (모니터링)
상태별 주문 수: RESERVED 0 / PRODUCING 0 / CONFIRMED 0 / RELEASE 1  (REJECTED 0, 참고)
시료별 재고: S-001 Logic Sample 재고 0 상태 고갈
```
→ 종료 전 만든 주문/재고가 그대로 남아 있음을 확인한다.

### 시나리오 4: 페이지네이션 (시료 12종 등록된 경우)

```
선택 > 1 -> 2 (시료 목록)
S-001 ... (10건 출력)
...외 2종 [N] 다음페이지
선택 > N
S-011, S-012 (나머지 2건 출력)
```

### 시나리오 5: 잘못된 입력 방어

```
선택 > 3 (승인/거절)
주문 ID > ORD-없는번호
오류: 해당 주문을 찾을 수 없습니다. (또는 RESERVED 상태가 아닙니다)
-> 메뉴로 돌아간다. 프로그램이 죽지 않는다.
```

## 5. 접근 방식

### 5.1 파일 구조

```text
sample_order/
├── cli.py      (신규) 메뉴 루프, rich 렌더링, 입력 처리 — 서비스 호출만 위임
seed.py는 이번 Phase 범위 밖(PLAN.md에서 별도 언급되지만 "더미 데이터 활용"은
  이미 별도 관심사이고, Phase 9 체크리스트는 메뉴/rich/load-save/경로 인자만
  요구한다 — seed 관련 메뉴 항목은 SPEC.md 10장 표에도 없으므로 추가하지 않는다).
main.py        (신규) 진입점: sys.argv로 경로 파싱 -> 서비스/레포지토리 조립 ->
                load_into -> cli 루프 시작 -> 종료 시 save
```

`cli.py` 내부는 ConsoleMVC PoC의 "입력/출력 담당 함수는 작게 쪼갠다" 관례를
참고하되, PLAN.md 2장의 예상 구조가 이미 `cli.py` 단일 파일로 못박아 두었으므로
별도 `view.py`/`controller.py`로 쪼개지 않는다. 대신 파일 내부를 아래처럼
역할별로 구획한다.

- **렌더링 함수** (`_render_*`, `_badge`, `_paginate`): rich `Console`/`Table`을
  사용해 화면을 그린다. 순수 출력만 하고 서비스를 호출하지 않는다.
- **입력 함수** (`_prompt_*`): `input()`을 감싸 값/취소를 반환한다.
- **메뉴 핸들러** (`_menu_sample`, `_menu_order_place`, `_menu_order_review`,
  `_menu_monitoring`, `_menu_production`, `_menu_release`): 입력을 받고, 서비스
  메서드를 호출하고, 결과 또는 예외 메시지를 렌더링한다.
- **`run(sample_service, order_service, production_line, monitoring_service)`**:
  6+1 메인 메뉴 루프. `main.py`가 조립한 서비스 인스턴스를 주입받는다(테스트에서도
  같은 방식으로 주입해 스모크 테스트 가능).

### 5.2 메뉴별 서비스 호출 매핑 (SPEC.md 10장 순서 그대로)

| 번호 | 메뉴 | 세부 동작 | 호출하는 서비스 메서드 | 표시 내용 |
|---|---|---|---|---|
| 1 | 시료 관리 | 1)등록 2)전체조회 3)검색 | `SampleService.register(Sample(...))` / `.list_all()` / `.search(keyword)` | 등록 결과 메시지, 시료 테이블(ID/이름/평균생산시간/수율/재고), 중복 ID면 `DuplicateSampleError` 메시지 |
| 2 | 시료 주문 | 시료ID/고객명/수량 입력 후 접수 | `OrderService.place_order(sample_id, customer_name, quantity)` | 새 주문 ID와 `RESERVED` 배지, 없는 시료면 `UnknownSampleError` 메시지 |
| 3 | 주문 승인/거절 | RESERVED 목록에서 주문 선택 후 승인/거절 | `OrderService.list_all()`로 RESERVED만 필터해 목록 표시 -> `OrderService.approve(order_id)` 또는 `.reject(order_id)` | 승인 결과 배지(`CONFIRMED`/`PRODUCING`), 거절 결과(`REJECTED`), RESERVED 아니면 `InvalidOrderStateError` 메시지 |
| 4 | 모니터링 | 상태별 집계 + 재고 상태 | `MonitoringService.order_status_counts()`, `.rejected_count()`, `.inventory_status()` | 상태별 건수 표(배지 색상), 시료별 재고 상태(여유/부족/고갈) 표 |
| 5 | 생산 라인 조회 | 현재 작업/대기 큐 확인, 시작, 완료 처리 | `ProductionLine.list_all()`로 IN_PROGRESS/QUEUED 구분 표시, `.start_next(now=...)`, `.complete_current(sample_service, order_service, now=...)` | 현재 작업(시작 시각), 대기 큐(FIFO 순서), 완료 시 재고 증가/주문 CONFIRMED 안내, 미완료면 `ProductionNotYetCompleteError`의 남은 시간 안내 |
| 6 | 출고 처리 | CONFIRMED 목록에서 선택 후 출고 | `OrderService.list_all()`로 CONFIRMED만 필터해 목록 표시 -> `OrderService.release(order_id)` | 출고 결과(`RELEASE` 배지, 차감된 재고), 재고 부족이면 `InsufficientStockError` 메시지 |
| 0 | 종료 | 저장 후 종료 | `Repository.save(sample_service, order_service, production_line)` | "저장 후 종료합니다" 안내 후 루프 종료 |

### 5.3 `main.py` 조립 순서

1. `path = sys.argv[1] if len(sys.argv) > 1 else "data.json"`
2. `sample_service = SampleService()`
3. `production_line = ProductionLine()`
4. `order_service = OrderService(sample_service, production_line=production_line)`
5. `monitoring_service = MonitoringService(sample_service, order_service)`
6. `repository = Repository(path)`
7. `repository.load_into(sample_service, order_service, production_line)`
   (파일이 없으면 `storage.load`가 빈 데이터를 반환하므로 빈 상태로 시작 —
   이미 Phase 8에서 보장된 동작)
8. `cli.run(sample_service, order_service, production_line, monitoring_service,
   on_exit=lambda: repository.save(sample_service, order_service, production_line))`
   (또는 `run`이 반환할 때 `main.py`가 직접 `repository.save(...)`를 호출하는
   형태도 가능 — 구현 시 더 단순한 쪽을 선택한다. 핵심 요구사항은 "종료 메뉴
   선택 시 저장이 실제로 실행된다"이다.)

### 5.4 rich 사용 범위

- 상태 배지: `rich.text.Text` 또는 `[color]TEXT[/color]` 마크업 문자열로
  상태별 색상을 고정 매핑한다(예: RESERVED=yellow, CONFIRMED=cyan,
  PRODUCING=magenta, RELEASE=green, REJECTED=red). 색상이 안 보여도 상태 문자열
  자체가 항상 함께 출력되므로 의미가 유지된다(SPEC.md 11장 요구).
- 테이블: `rich.table.Table`로 시료/주문/생산작업/모니터링 목록을 표로 그린다.
- 페이지네이션: 목록 함수가 공통으로 쓰는 `_paginate(items, page_size=10)`
  헬퍼를 두고, 페이지 크기를 넘는 목록에는 마지막 줄에 `...외 N종 [N] 다음페이지`
  안내를 붙인다. 사용자가 `N`을 입력하면 다음 페이지를 그린다.

## 6. 가정/리스크/트레이드오프

1. **seed.py는 이번 Phase에 만들지 않는다.** PLAN.md 2장 예상 구조에는
   `seed.py`가 있지만, Phase 9 목표 문단과 SPEC.md 10장 메뉴 표 어디에도
   "더미 데이터 적재" 메뉴 항목이 없다. CLAUDE.md 4장도 "더미/시드 데이터는
   프로그램 자동 적재가 아니라 명시적 명령/옵션으로만 넣는다"고만 규정할 뿐
   이번 Phase 필수 요구는 아니다. 과잉 구현을 피하기 위해 seed 데이터 생성은
   범위에서 제외하고, 필요하면 후속 작업으로 남긴다.
2. **주문 목록 필터링은 `cli.py`에서 `list_all()` 결과를 status로 걸러서 만든다.**
   `OrderService`에 상태별 조회 메서드를 새로 추가할 수도 있지만, 이미 존재하는
   `list_all()`만으로 충분하고 도메인 서비스에 콘솔 전용 조회 메서드를 얹는 것은
   불필요한 확장이라고 판단했다. (대안: `OrderService.list_by_status(status)`를
   추가하는 방법도 있었으나, "도메인 로직은 콘솔 입출력과 분리한다"는 원칙과
   무관하게 순수 필터링이라 `cli.py`에서 처리해도 계층 위반이 아니다 — 이 필터는
   상태 판단/계산이 아니라 단순 화면 표시용 선택이기 때문이다.)
3. **`now()` 주입**: 생산 작업 시작/완료 처리 메뉴는 `ProductionLine.start_next`/
   `complete_current`가 요구하는 `now` 콜러블 인자에 기본값(`datetime.now`)을
   그대로 넘긴다. CLI 계층에서 시간을 조작할 필요는 없다(실사용 흐름이므로).
4. **종료 시 저장 실패 처리**: `Repository.save`가 예외를 던지는 경우(예: 쓰기
   권한 없음)는 이번 Phase 범위에서 세밀하게 다루지 않는다. SPEC.md/PLAN.md
   어디에도 저장 실패 시 별도 복구 절차를 요구하지 않으므로, 예외가 나면
   그대로 전파되는 최소 동작으로 둔다(과잉 방어 로직 추가 지양).
5. **입력 검증 실패(숫자가 아닌 수량 등)**: `ValueError`를 잡아 "메뉴로
   돌아간다"는 최소 방어만 구현한다. 이는 DataPersistence PoC의 `main.py`도
   동일하게 `try/except ValueError`로 처리한 패턴을 참고한 것이다.
6. **CLI 테스트 범위**: PLAN.md 6장은 "CLI는 최소 smoke test와 수동 시나리오로
   검증한다"고 명시한다. 따라서 `tests/test_sample_order_cli.py`는 메뉴 전체를
   자동화하기보다, 서비스 조립과 렌더링 헬퍼(배지 매핑, 페이지네이션 경계값)
   같은 순수 함수 단위의 대표 테스트 몇 개로 제한한다. 실제 메뉴 입력 루프
   검증은 수동 시나리오(위 5개)로 대체한다 — 이는 임의 축소가 아니라 PLAN.md에
   이미 명시된 검증 전략을 그대로 따르는 것이다.

## 7. 검증 방법

- `PYTHONPATH=. pytest -q` 전체 테스트가 통과한다(기존 8개 Phase 테스트 + 신규
  `tests/test_sample_order_cli.py`).
- 위 대표 시나리오 1~5를 실제로 `python3 main.py <임시경로>.json`을 실행해
  수동으로 따라가며 확인한다. 특히 시나리오 3(재실행 후 복원)은 프로그램을
  완전히 종료했다가 같은 경로로 다시 실행해서 확인한다.
- `sample_order/domain.py`/`services.py`/`production.py`/`monitoring.py`에
  `print`/`input`이 없는지 grep으로 재확인한다(계층 분리 유지 확인).
- `cli.py`가 상태 전이/생산량 계산을 다시 구현하지 않고 기존 서비스 메서드만
  호출하는지 코드 리뷰로 확인한다(5.2절의 매핑표와 실제 구현이 일치하는지 대조).

