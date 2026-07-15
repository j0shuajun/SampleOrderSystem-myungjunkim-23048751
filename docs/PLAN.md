# PLAN: Semiconductor Sample Order System

## 1. 전체 전략

메인 프로젝트는 TDD로 진행한다. PoC 4개는 참고 자료로 사용하되, 메인 프로젝트는 독립 실행
가능해야 한다.

구현은 도메인 로직부터 시작하고, 콘솔 UI는 나중에 붙인다.

우선순위:

1. 상태 전이와 계산이 정확한 도메인 모델
2. 저장/불러오기
3. 콘솔 메뉴
4. 더미 데이터와 시연 편의 기능

## 2. 권장 구현 언어와 구조

구현 언어는 **Python**으로 확정한다.

예상 구조:

```text
SampleOrderSystem-myungjunkim-23048751/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── PRD.md
│   ├── SPEC.md
│   └── PLAN.md
├── sample_order/
│   ├── __init__.py
│   ├── domain.py
│   ├── services.py
│   ├── repository.py
│   ├── production.py
│   ├── monitoring.py
│   ├── seed.py
│   └── cli.py
├── tests/
│   ├── test_sample_order_domain.py
│   ├── test_sample_order_services.py
│   ├── test_sample_order_repository.py
│   ├── test_sample_order_production.py
│   ├── test_sample_order_monitoring.py
│   └── test_sample_order_cli.py
├── requirements.txt
├── requirements-dev.txt
└── main.py
```

콘솔 화면(상태 배지 색상, 테이블, 페이지네이션)은 `rich` 라이브러리로 구현한다.
`requirements.txt`에 `rich`를, `requirements-dev.txt`에 `pytest`를 등록한다. `rich`
렌더링은 `cli.py` 계층에만 두고, 도메인 모듈(`domain.py`/`services.py`/`production.py`/
`monitoring.py`)은 `rich`에 의존하지 않는다.

## 3. TDD 단계

### Phase 0: 프로젝트 기반

목표:

- 실행 환경과 테스트 환경을 만든다 (`requirements.txt`/`requirements-dev.txt`에
  `rich`, `pytest` 등록).
- README에 실행 방법을 적는다.

검증:

- 빈 테스트 또는 smoke test가 통과한다.

### Phase 1: 시료 모델과 시료 관리

목표:

- 시료 등록, 조회, 검색을 구현한다.
- 수율과 생산시간 필드를 가진다.

대표 테스트:

- 시료 등록 후 목록에서 조회된다.
- 이름 검색으로 시료를 찾는다.
- 중복 ID 등록을 막는다.

### Phase 2: 주문 접수와 상태 모델

목표:

- 주문을 접수하고 `RESERVED` 상태를 부여한다.
- 없는 시료에 대한 주문을 막는다.

대표 테스트:

- 주문 접수 시 `RESERVED` 상태다.
- 없는 시료 ID는 실패한다.

### Phase 3: 승인/거절

목표:

- `RESERVED` 주문을 승인 또는 거절한다.
- 가용재고(= 시료 재고 - 다른 미출고 주문 합계, SPEC.md 5.1) 충분 주문은 `CONFIRMED`로
  간다.
- 거절 주문은 `REJECTED`로 간다.

대표 테스트:

- 가용재고 충분 주문 승인 시 `CONFIRMED`.
- 이미 `PRODUCING`인 주문이 있어 가용재고가 raw 재고보다 적을 때, 새 주문이
  raw 재고만으로는 충분해 보여도 가용재고 기준으로 부족 판정된다 (이중 확정 방지).
- 주문 거절 시 `REJECTED`.
- `REJECTED` 주문은 다시 승인할 수 없다.

### Phase 4: 생산 큐와 재고 부족 처리

목표:

- 가용재고 부족 주문 승인 시 `PRODUCING`으로 전환하고 작업 시작 시각을 기록한다.
- 생산 작업을 FIFO 큐에 추가한다.
- 생산량을 `ceil(부족분 / 수율)`로 계산한다 (부족분은 가용재고 기준).

대표 테스트:

- 부족분과 수율로 계획 생산량을 계산한다.
- 여러 작업이 FIFO 순서로 처리된다.
- 먼저 승인된 주문이 재고를 committed로 선점해, 나중 주문의 부족분 계산에 반영된다.

### Phase 5: 생산 완료

목표:

- 작업 시작 후 총생산시간(`평균생산시간 × 계획생산량`)만큼 실제 경과 시간이 지나야
  완료 처리할 수 있다. 시간 소스는 테스트에서 mocking 가능하게 분리한다.
- 경과 시간이 부족하면 완료 처리를 거부하고 남은 시간을 안내한다.
- 완료 조건을 만족하면 재고를 증가시키고 연결 주문을 `CONFIRMED`로 전환한다.

대표 테스트:

- 총생산시간이 지나기 전 완료 처리를 시도하면 거부된다.
- 총생산시간이 지난 후 완료 처리하면 주문 상태가 `CONFIRMED`가 된다.
- 재고가 생산 결과만큼 증가한다.

### Phase 6: 출고 처리

목표:

- `CONFIRMED` 주문을 출고한다.
- 재고를 차감하고 주문을 `RELEASE`로 전환한다.

대표 테스트:

- 출고 후 상태는 `RELEASE`.
- 출고 후 재고가 주문 수량만큼 감소한다.
- `CONFIRMED`가 아닌 주문은 출고할 수 없다.

### Phase 7: 모니터링

목표:

- 상태별 주문 수를 보여준다.
- 시료별 재고 상태를 계산한다.
- `REJECTED`는 정상 집계에서 제외한다.

대표 테스트:

- 상태별 집계가 맞다.
- `REJECTED`가 정상 집계에 포함되지 않는다.
- 재고 상태가 여유/부족/고갈로 계산된다.

### Phase 8: 영속성

목표:

- 시료, 주문, 생산 작업, 재고를 저장하고 복원한다.

대표 테스트:

- 저장 후 다시 불러오면 같은 데이터가 복원된다.
- 파일이 없으면 빈 저장소로 시작한다.

### Phase 9: 콘솔 UI 통합

목표:

- 필수 메뉴를 콘솔에서 실행할 수 있게 한다.
- 도메인 로직과 입출력 경계를 분리한다.
- `rich`로 상태 배지 컬러, 테이블, 페이지네이션을 구현한다 (SPEC.md 11장).

대표 검증:

- 수동 시나리오로 주문 접수부터 출고까지 진행한다.
- CLI가 도메인 서비스 테스트를 깨지 않는다.

## 4. PoC 사용 계획

| PoC | 메인 프로젝트 적용 방식 |
|---|---|
| ConsoleMVC | `cli.py`와 서비스 경계 설계 참고 |
| DataPersistence | JSON repository 구현 참고 |
| DataMonitor | `monitoring.py` 집계 기준 참고 |
| DummyDataGenerator | `seed.py` 또는 샘플 데이터 생성 참고. DataPersistence와 동일한 JSON 스키마(`S-XXX`/`ORD-YYYYMMDD-NNNN` ID 포맷 포함)로 출력하도록 맞춘다 |

복사 정책:

- PoC 코드를 그대로 사용해야 한다면 메인 repo 내부에 복사한다.
- 예: `sample_order/poc_references/` 또는 실제 모듈로 흡수.
- 복사 후에도 메인 repo는 PoC repo 없이 실행되어야 한다.
- README에 원본 Git URL과 사용 목적을 기록한다.

PoC 원격 URL:

- `https://github.com/j0shuajun/ConsoleMVC-myungjunkim-23048751.git`
- `https://github.com/j0shuajun/DataPersistence-myungjunkim-23048751.git`
- `https://github.com/j0shuajun/DataMonitor-myungjunkim-23048751.git`
- `https://github.com/j0shuajun/DummyDataGenerator-myungjunkim-23048751.git`

## 5. 커밋 계획

문서 초기화:

```text
docs: define semiconductor sample order system plan
```

각 TDD phase:

```text
test: add reserved order creation scenario
feat: create orders in reserved state
```

필요 시:

```text
refactor: separate order approval service
fix: exclude rejected orders from monitoring totals
```

## 6. 검증 전략

- 도메인 계산과 상태 전이는 자동 테스트로 검증한다.
- 저장소는 임시 파일을 사용해 저장/복원 테스트를 한다.
- CLI는 최소 smoke test와 수동 시나리오로 검증한다.
- 최종 수동 시나리오는 다음 흐름을 포함한다.

```text
시료 등록
-> 주문 접수
-> 재고 부족 승인
-> 생산 큐 확인
-> 생산 완료
-> 출고
-> 모니터링 확인
-> 재실행 후 데이터 복원 확인
```

## 7. 완료 체크리스트

- [ ] 시료 관리 완료
- [ ] 주문 접수 완료
- [ ] 승인/거절 완료
- [ ] 생산 큐 완료
- [ ] 생산 완료 처리 완료
- [ ] 출고 처리 완료
- [ ] 모니터링 완료
- [ ] 영속성 완료
- [ ] 콘솔 UI 통합 완료
- [ ] README 작성
- [ ] PoC 재사용 여부와 출처 기록
- [ ] 전체 테스트 통과
- [ ] 대표 수동 시나리오 통과
