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

### 재고 충분

조건:

```text
sample.stock >= order.quantity
```

결과:

- 주문 상태를 `CONFIRMED`로 바꾼다.
- 이 시점에서는 출고 전이므로 재고 차감은 출고 처리에서 한다.
- 생산 큐에는 아무 작업도 추가하지 않는다.

### 재고 부족

조건:

```text
sample.stock < order.quantity
```

계산:

```text
shortage = order.quantity - sample.stock
planned_quantity = ceil(shortage / sample.yield_rate)
total_production_time = sample.average_production_time * planned_quantity
```

결과:

- 주문 상태를 `PRODUCING`으로 바꾼다.
- 생산 작업을 FIFO 큐 뒤에 추가한다.
- 생산 작업에는 주문 ID, 시료 ID, 부족분, 계획 생산량, 예상 생산 시간이 포함된다.

비고: `planned_quantity`는 부족분에 대한 수율 손실을 이미 보정한 최종 생산량이다.
부족분 이상으로 별도의 안전재고(버퍼)를 추가로 확보하지 않는다.

## 6. 생산 라인

생산 라인은 하나의 작업을 순서대로 처리한다.

기능:

- 현재 생산 중인 작업 보기
- 대기 중인 생산 큐 보기
- 다음 생산 작업 시작
- 생산 완료 처리

생산 완료 결과:

- 생산된 정상 시료 수량만큼 재고를 증가시킨다.
- 연결된 주문 상태를 `CONFIRMED`로 바꾼다.
- 작업 상태를 완료로 바꾼다.

PoC 수준에서는 실제 시간 흐름을 기다리지 않아도 된다. 사용자의 명령으로 생산 완료를 처리할 수 있다.

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
- 생산 완료 후 주문은 `CONFIRMED`가 된다.
- `CONFIRMED` 주문 출고 후 상태는 `RELEASE`가 되고 재고가 차감된다.
- 모니터링에서 `REJECTED`는 정상 집계에서 제외된다.
- 저장 후 재실행하면 데이터가 복원된다.
