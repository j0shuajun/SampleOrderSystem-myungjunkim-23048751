# SampleOrderSystem — 반도체 시료 생산주문관리 시스템

가상의 반도체 회사 "S-Semi"의 시료(Sample) 주문·재고·생산·출고를 콘솔(CLI)에서
관리하는 시스템입니다. 반도체 시료 생산주문관리 시스템 과제의 **메인 프로젝트**이며,
그 자체로 독립 실행 가능합니다.

## 이 시스템이 해결하는 문제

엑셀과 메모장으로 주문을 관리하다 보니 실수가 잦고, 재고와 공정 현황을 한눈에
파악하기 어려웠습니다. 이 시스템은 아래 질문에 즉시 답할 수 있게 합니다.

- 이 주문은 접수만 된 상태인가, 승인된 상태인가?
- 재고가 충분해서 바로 출고할 수 있는가?
- 재고가 부족하다면 생산 라인에 들어갔는가?
- 생산이 끝나면 어떤 주문을 출고해야 하는가?

## 주요 기능

| 메뉴 | 기능 |
|---|---|
| 시료 관리 | 시료 등록, 목록 조회, 이름 검색 |
| 시료 주문 | 고객 주문 접수 (`RESERVED` 생성) |
| 주문 승인/거절 | 재고 충분 시 `CONFIRMED`, 부족 시 `PRODUCING`(생산 큐 등록), 거절 시 `REJECTED` |
| 모니터링 | 주문 상태별 건수, 시료별 재고 상태(여유/부족/고갈) |
| 생산 라인 조회 | 현재 생산 중인 작업과 FIFO 대기 큐 확인, 생산 완료 처리 |
| 출고 처리 | `CONFIRMED` 주문을 출고하고 `RELEASE`로 전환 |

## 주문 상태 흐름

```text
RESERVED -> REJECTED
RESERVED -> CONFIRMED   (승인 + 재고 충분)
RESERVED -> PRODUCING   (승인 + 재고 부족) -> CONFIRMED (생산 완료)
CONFIRMED -> RELEASE    (출고 완료)
```

재고 부족 시 실제 생산량은 `ceil(부족분 / 수율)`로 계산하며, 별도의 안전재고(버퍼)는
추가하지 않습니다.

## 실행 환경

- 구현 언어: Python
- 데이터 저장: JSON 파일 (재실행 후에도 데이터 유지)
- 실행 방식: 콘솔(CLI) 메뉴 기반

## 문서

- [`docs/PRD.md`](docs/PRD.md): 왜 이 시스템이 필요한지, 대표 사용자 흐름
- [`docs/SPEC.md`](docs/SPEC.md): 시료·주문·재고·생산·출고·모니터링 상세 동작 명세
- [`docs/PLAN.md`](docs/PLAN.md): TDD 진행 순서와 검증 전략
- [`CLAUDE.md`](CLAUDE.md): 개발 방식(Verify Harness 서브에이전트 파이프라인)과 작업 규칙

## 참고한 PoC 저장소

아래 4개 PoC에서 검증한 구조를 참고하거나 일부 재사용했습니다. 이 메인 프로젝트는
PoC 코드에 직접 의존하지 않고, 필요한 부분은 내부에 독립적으로 복사/재작성했습니다.

| PoC | Repository | 참고 목적 |
|---|---|---|
| 콘솔 MVC 구조 | [ConsoleMVC-myungjunkim-23048751](https://github.com/j0shuajun/ConsoleMVC-myungjunkim-23048751) | Model/View/Controller 책임 분리와 CLI 경계 설계 |
| 데이터 영속성 | [DataPersistence-myungjunkim-23048751](https://github.com/j0shuajun/DataPersistence-myungjunkim-23048751) | JSON 저장소와 CRUD 흐름 |
| 데이터 모니터링 | [DataMonitor-myungjunkim-23048751](https://github.com/j0shuajun/DataMonitor-myungjunkim-23048751) | 상태별 집계 기준과 콘솔 표시 방식 |
| Dummy 데이터 생성 | [DummyDataGenerator-myungjunkim-23048751](https://github.com/j0shuajun/DummyDataGenerator-myungjunkim-23048751) | seed/더미 데이터 생성 방식과 스키마 |
