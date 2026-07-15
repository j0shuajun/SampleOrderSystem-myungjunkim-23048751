# SPEC: Semiconductor Sample Order System

## 1. 도메인 용어

| 용어 | 의미 |
|---|---|
| Sample | 생산/주문 대상인 반도체 시료 |
| Order | 고객이 특정 시료와 수량을 요청한 주문 |
| Inventory | 시료별 현재 재고 |
| Production Line | 재고 부족 주문을 FIFO로 생산하는 라인 |
| Production Job | 특정 주문의 부족분을 생산하기 위한 작업 |

## 2. 시료

시료는 시스템에 등록된 것만 주문 가능하다.

필드:

| 필드 | 설명 |
|---|---|
| sample_id | 시료 고유 ID. 형식은 `S-001`처럼 `S-` + 3자리 이상 일련번호 |
| name | 시료 이름 |
| average_production_time | 시료 1개 평균 생산 시간 |
| yield_rate | 수율. 0보다 크고 1 이하 |
| stock | 현재 재고 수량 |

기능:

- 시료 등록
- 전체 시료 조회
- 이름 또는 속성 기반 검색
- 현재 재고 함께 표시

## 3. 주문

주문 ID는 `ORD-YYYYMMDD-0000` 형식(접수일 + 4자리 일련번호)으로 시스템이 자동 부여한다.

주문 접수 입력값:

| 입력 | 설명 |
|---|---|
| sample_id | 주문 대상 시료 ID |
| customer_name | 고객명 |
| quantity | 주문 수량 |

주문 상태:

| 상태 | 의미 | 모니터링 포함 여부 |
|---|---|---|
| `RESERVED` | 주문 접수 | 포함 |
| `REJECTED` | 주문 거절 | 제외 |
| `PRODUCING` | 승인 완료, 재고 부족으로 생산 중 | 포함 |
| `CONFIRMED` | 승인 완료, 출고 대기 중 | 포함 |
| `RELEASE` | 출고 완료 | 포함 |

## 4. 주문 상태 흐름

```text
RESERVED
  -> REJECTED
  -> CONFIRMED   (승인 + 재고 충분)
  -> PRODUCING   (승인 + 재고 부족)

PRODUCING
  -> CONFIRMED   (생산 완료)

CONFIRMED
  -> RELEASE     (출고 완료)
```

금지:

- `REJECTED`에서 다른 상태로 전환하지 않는다.
- `RELEASE`에서 다른 상태로 전환하지 않는다.
- `RESERVED`가 아닌 주문은 승인/거절할 수 없다.
- `CONFIRMED`가 아닌 주문은 출고할 수 없다.

## 5. 승인 처리

승인 대상은 `RESERVED` 주문이다.

### 5.1 가용재고와 우선순위 원칙

승인 판단은 시료의 raw `stock` 값이 아니라 **가용재고(available stock)** 를 기준으로
한다.

```text
committed = 이 시료를 대상으로 하는 다른 주문 중 PRODUCING 또는 CONFIRMED 상태인
            주문의 수량 합계 (지금 심사 중인 주문 자신과 RESERVED 주문은 제외)
available = max(0, sample.stock - committed)
```

`RESERVED`는 아직 승인/거절이 결정되지 않은 주문이므로 committed에 포함하지 않는다.
committed는 **이미 승인되어 확정된(재고를 실제로 약속받은) 주문만** 집계한다. 이는
8장(모니터링)의 "미출고 주문 합계"(RESERVED 포함)와는 다른 계산이다 — 모니터링은
운영자에게 "앞으로 나갈 수요"를 넓게 보여주는 용도이고, 이 승인 판단은 "이미 확정된
약속"만 보호하는 용도이기 때문이다.

우선순위 원칙: **먼저 승인되어 `PRODUCING`/`CONFIRMED`가 된 주문이 재고에 대한 우선권을
가진다.** 나중에 심사되는 주문은 앞선 주문들이 이미 committed로 잡아 둔 몫을 제외한
나머지 가용재고만 사용할 수 있다. `sample.stock` 필드 자체는 실물 재고를 그대로
나타내야 하므로, 승인 시점에 물리적으로 차감하지 않는다 — 대신 이 가용재고 계산으로
이중 확정(여러 주문이 같은 재고를 중복해서 약속받는 상황)을 막는다.

예시: 재고 70에 주문 A(100)가 먼저 승인되어 부족분 30으로 `PRODUCING`이 되면, A는
committed 100으로 잡힌다. 이어서 주문 B(20)를 심사하면
`available = max(0, 70 - 100) = 0`이므로 B는 재고가 있어 보여도(raw stock=70) 즉시
`CONFIRMED`되지 않고, 부족분 20에 대해 별도로 `PRODUCING`에 들어간다. 반면 B가 아직
`RESERVED`인 상태로 접수만 되어 있었다면(승인 전), 그 사이 다른 주문 C를 심사할 때
B의 수량은 committed에 반영되지 않는다.

### 재고 충분

조건:

```text
available >= order.quantity
```

결과:

- 주문 상태를 `CONFIRMED`로 바꾼다.
- 이 시점에서는 출고 전이므로 `sample.stock` 차감은 출고 처리에서 한다.
- 생산 큐에는 아무 작업도 추가하지 않는다.

### 재고 부족

조건:

```text
available < order.quantity
```

계산:

```text
shortage = order.quantity - available
planned_quantity = ceil(shortage / sample.yield_rate)
total_production_time = sample.average_production_time * planned_quantity
```

결과:

- 주문 상태를 `PRODUCING`으로 바꾼다.
- 생산 작업을 FIFO 큐 뒤에 추가한다.
- 생산 작업에는 주문 ID, 시료 ID, 부족분, 계획 생산량, 예상 생산 시간, 작업 시작 시각이
  포함된다.

비고: `planned_quantity`는 부족분에 대한 수율 손실을 이미 보정한 최종 생산량이다.
부족분 이상으로 별도의 안전재고(버퍼)를 추가로 확보하지 않는다.

## 6. 생산 라인

생산 라인은 단일 라인이며, 하나의 작업을 FIFO 순서로 처리한다(동시에 두 작업을
진행하지 않는다).

기능:

- 현재 생산 중인 작업 보기
- 대기 중인 생산 큐 보기
- 다음 생산 작업 시작 (시작 시각을 기록한다)
- 생산 완료 처리

### 완료 판정 기준

생산 완료는 담당자의 "생산 완료 처리" 명령으로 트리거하되, 판정은 실제 경과 시간에
근거한다.

```text
elapsed = 현재 시각 - 작업 시작 시각
완료 조건: elapsed >= total_production_time
```

- 조건을 만족하지 못하면 완료를 거부하고 남은 시간을 안내한다. 작업 상태는 그대로
  유지된다(부분 생산량이라는 개념은 두지 않는다 — 완료 전에는 "진행 중"만 존재한다).
- 조건을 만족하면 아래 "생산 완료 결과"를 그대로 적용한다.
- 현재 시각은 `now()` 형태의 콜러블을 주입받아 얻는다(기본값은 `datetime.now`).
  테스트에서는 이 콜러블만 교체해 시간 경과를 재현한다. 같은 시료에 생산 작업이 여러
  개 큐에 쌓여도 각 작업은 병합하지 않고 별개로 FIFO 처리한다.

생산 완료 결과:

- 생산된 정상 시료 수량만큼 `sample.stock`을 증가시킨다.
- 연결된 주문 상태를 `CONFIRMED`로 바꾼다.
- 작업 상태를 완료로 바꾼다.

## 7. 출고

출고 대상은 `CONFIRMED` 주문이다.

출고 조건:

```text
sample.stock >= order.quantity
```

출고 결과:

- 시료 재고를 주문 수량만큼 차감한다.
- 주문 상태를 `RELEASE`로 바꾼다.

재고가 부족하면 출고를 막고 오류를 보여준다. 정상 흐름에서는 생산 완료 후 충분해야 한다.

## 8. 모니터링

### 주문 상태별 집계

표시 상태:

- `RESERVED`
- `PRODUCING`
- `CONFIRMED`
- `RELEASE`

`REJECTED`는 별도 참고 정보로 표시할 수 있지만 정상 집계에서는 제외한다.

### 시료별 재고 상태

| 상태 | 기준 |
|---|---|
| 여유 | 현재 재고가 미출고 주문 수량 이상 |
| 부족 | 현재 재고가 0보다 크지만 미출고 주문 수량보다 적음 |
| 고갈 | 현재 재고가 0 |

미출고 주문 수량은 `RESERVED`, `PRODUCING`, `CONFIRMED` 주문을 기준으로 계산한다.

## 9. 데이터 영속성

프로그램을 다시 실행해도 아래 데이터가 유지되어야 한다.

- 시료
- 주문
- 생산 작업
- 재고

기본 저장 방식은 JSON 파일을 우선 고려한다. 외부 DB는 필수로 두지 않는다.

## 10. 콘솔 메뉴

PDF 데모 화면 기준으로 주문 접수와 승인/거절을 분리한 6+1 메뉴 구성을 따른다.

| 번호 | 메뉴 | 기능 |
|---|---|---|
| 1 | 시료 관리 | 등록, 조회, 검색 |
| 2 | 시료 주문 | 고객 주문 접수 (`RESERVED` 생성) |
| 3 | 주문 승인/거절 | `RESERVED` 주문의 승인·거절 처리 |
| 4 | 모니터링 | 주문 상태별 수, 시료별 재고 상태 |
| 5 | 생산 라인 조회 | 현재 작업과 대기 큐 확인, 생산 완료 처리 |
| 6 | 출고 처리 | `CONFIRMED` 주문 출고 |
| 0 | 종료 | 저장 후 종료 |

## 11. 콘솔 화면 디자인

- 상태 배지(`RESERVED`/`CONFIRMED`/`PRODUCING`/`RELEASE`/`REJECTED`)는 ANSI 컬러로
  구분해 표시한다. 터미널이 ANSI를 지원하지 않는 환경을 고려해 색상 없이도 상태 라벨
  텍스트만으로 의미가 통하게 한다.
- 시료/주문 목록이 한 화면 분량을 넘으면 PDF 데모처럼 페이지네이션
  (`...외 N종 [N] 다음페이지`)을 적용한다. 전체를 한 번에 출력하지 않는다.
- 그 외 화면 레이아웃은 PDF 예시 UI를 참고하되 자유롭게 구성한다.

## 12. ID 포맷

| 대상 | 형식 | 예시 |
|---|---|---|
| 시료 ID | `S-` + 3자리 이상 일련번호 | `S-001` |
| 주문 ID | `ORD-` + 접수일(YYYYMMDD) + `-` + 4자리 일련번호 | `ORD-20260416-0001` |

## 13. 예시 데이터

```json
{
  "samples": [
    {
      "sample_id": "S-001",
      "name": "Logic Sample",
      "average_production_time": 5,
      "yield_rate": 0.9,
      "stock": 3
    }
  ],
  "orders": [
    {
      "order_id": "ORD-20260416-0001",
      "sample_id": "S-001",
      "customer_name": "Fabless A",
      "quantity": 10,
      "status": "RESERVED"
    }
  ],
  "production_jobs": []
}
```

## 14. 주요 테스트 시나리오

- 시료를 등록하면 목록과 검색에서 조회된다.
- 없는 시료 ID로 주문하면 실패한다.
- 주문 접수 시 상태는 `RESERVED`다.
- `RESERVED` 주문을 거절하면 `REJECTED`가 된다.
- 재고 충분 주문 승인 시 `CONFIRMED`가 된다.
- 재고 부족 주문 승인 시 `PRODUCING`이 되고 생산 작업이 추가된다.
- 생산량은 `ceil(부족분 / 수율)`로 계산된다.
- 생산 큐는 FIFO로 처리된다.
- 이미 `PRODUCING`인 주문이 재고를 미출고 상태로 committed하고 있으면, raw 재고만
  보고 충분해 보이는 새 주문도 가용재고 기준으로 재계산해 부족분만큼 `PRODUCING`으로
  들어간다 (이중 확정 방지).
- 생산 작업 시작 후 총생산시간이 지나기 전에 완료 처리를 시도하면 거부된다.
- 총생산시간이 지난 뒤 완료 처리하면 주문은 `CONFIRMED`가 되고 재고가 증가한다.
- `CONFIRMED` 주문 출고 후 상태는 `RELEASE`가 되고 재고가 차감된다.
- 모니터링에서 `REJECTED`는 정상 집계에서 제외된다.
- 저장 후 재실행하면 데이터가 복원된다.
