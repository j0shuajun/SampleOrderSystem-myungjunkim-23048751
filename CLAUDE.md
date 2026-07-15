# CLAUDE.md

이 저장소는 반도체 시료 생산주문관리 시스템 과제의 **메인 프로젝트**다.
PoC 4개 저장소에서 검증한 구조와 도구를 참고하거나 복사해 사용할 수 있지만, 이 저장소는
그 자체로 독립 실행 가능해야 한다.

## 1. Source of Truth

아래 문서를 기준으로 구현한다.

- `docs/PRD.md`: 왜 이 시스템이 필요한지, 누가 어떤 문제를 해결하는지 설명하는 제품 문서.
- `docs/SPEC.md`: 시료, 주문, 재고, 생산 라인, 출고, 모니터링의 상세 동작 명세.
- `docs/PLAN.md`: TDD 진행 순서, 구현 단계, 검증 전략, PoC 재사용 계획.

구현 중 판단이 흔들리면 우선순위는 다음과 같다.

1. 과제 PDF의 기능 명세
2. `docs/SPEC.md`
3. `docs/PRD.md`
4. `docs/PLAN.md`
5. 코드의 현재 구현

문서와 코드가 충돌하면 코드를 임의로 맞추기 전에 문서를 먼저 갱신하거나, 사용자에게 확인한다.

## 2. 개발 방식

이 메인 프로젝트는 PoC와 달리 TDD를 꼼꼼하게 적용하고, "Verify Harness" 서브에이전트
파이프라인으로 사람이 리뷰하기 전에 AI 스스로 먼저 검증하게 한다. 이 하네스 구조는
`../Day17/harness` PoC에서 검증한 4-서브에이전트 패턴을 이 프로젝트 도메인에 맞게
가져온 것이다 (`.claude/agents/` 참고).

오케스트레이션은 **수동/대화형**으로 진행한다. Phase 자동 일괄 처리(스크립트로
Phase 0~9를 한 번에 돌리는 방식)는 쓰지 않는다 — Phase 하나씩 아래 서브에이전트를
순서대로 호출하고, 각 단계 결과(PASS/FAIL)를 사람이 확인한 뒤 다음으로 넘어간다.

기본 사이클은 **RED → GREEN → REVIEW**이며, 각 단계는 아래 서브에이전트가 담당한다.

### RED

1. 이번 Phase(`docs/PLAN.md` 기준)에서 구현할 사용자-visible behavior를 하나 정한다.
2. `doc-consistency-verifier` 서브에이전트로 `docs/PRD.md`/`docs/SPEC.md`/`docs/PLAN.md`
   간 충돌·모호성이 없는지 확인한다. **PASS를 받기 전에는 구현을 시작하지 않는다.**
   FAIL이면 문서를 먼저 수정하고 재검증한다.
3. `ai-action`이 `docs/tasks/yyyy-mm-dd_<phase>_plan.md`를 작성한다(아직 커밋·테스트·
   구현은 착수하지 않는다).
4. **plan 문서를 사람에게 보고하고 승인을 받는다.** 이번 Phase에서 무엇을, 어떤
   순서로 구현할지 사람이 확인하기 전에는 커밋도, 다음 단계(테스트 작성)도 하지 않는다.
5. 승인을 받은 뒤에야 plan 문서를 `docs:` 커밋한다.
6. 승인 후 `ai-action`이 실패해야 하는 테스트를 작성하고, 실제로 실패하는지 확인한다.
7. 테스트 변경을 `test:` 커밋으로 남긴다.

### GREEN

1. `ai-action`이 테스트를 통과시키는 최소 구현을 작성한다.
2. 관련 테스트를 실행한다.
3. 필요하면 전체 테스트(`PYTHONPATH=. pytest -q`)를 실행한다.

### REVIEW

1. `test-verifier`와 `compliance-verifier`를 **병렬로** 실행한다.
   - Test Verify: pytest 결과(Correctness) + SPEC.md의 대표 시나리오를 직접 재현.
   - Compliance Verify: 테스트 통과 여부와 무관하게 PLAN.md/SPEC.md의 요구사항을
     코드와 하나씩 대조.
   - 서로 다른 관점의 검증이므로 어느 한쪽만 통과해도 "완료"로 보지 않는다.
2. 구현이 이번 Phase 범위를 넘지 않았는지, 불필요한 추상화·임의 기능·UI 과잉 구현이
   없는지 확인한다.
3. **두 검증이 모두 PASS여도 자동으로 다음 Phase로 넘어가지 않는다.** Phase마다 변경
   요약(무엇을 구현했는지, 두 검증 결과, 커밋 목록)을 사람에게 보고하고, 사람이 명시적으로
   승인("다음 Phase 진행")한 뒤에만 다음 Phase의 RED를 시작한다. FAIL 여부와 무관하게
   이 사람 승인 단계 자체를 생략하지 않는다.
4. 구현 커밋을 `feat:`, 버그 수정이면 `fix:`, 구조 개선이면 `refactor:`로 남긴다.

## 3. PoC 재사용 정책

PoC 저장소는 다음 목적으로 사용할 수 있다.

| PoC 저장소 | Git URL | 사용 목적 |
|---|---|---|
| `ConsoleMVC-myungjunkim-23048751` | `https://github.com/j0shuajun/ConsoleMVC-myungjunkim-23048751.git` | 콘솔 MVC 구조 참고 |
| `DataPersistence-myungjunkim-23048751` | `https://github.com/j0shuajun/DataPersistence-myungjunkim-23048751.git` | JSON 저장소와 CRUD 흐름 참고 |
| `DataMonitor-myungjunkim-23048751` | `https://github.com/j0shuajun/DataMonitor-myungjunkim-23048751.git` | 모니터링 집계 기준과 콘솔 표시 참고 |
| `DummyDataGenerator-myungjunkim-23048751` | `https://github.com/j0shuajun/DummyDataGenerator-myungjunkim-23048751.git` | seed/dummy 데이터 생성 방식 참고 |

메인 repo가 독립적으로 동작해야 하므로 PoC 코드를 직접 의존성으로 두지 않는다.
필요한 코드는 메인 repo 내부에 복사하거나 같은 역할의 모듈로 다시 작성한다.

복사하거나 강하게 참고한 경우에는 다음을 README 또는 관련 문서에 기록한다.

- 원본 Git URL
- 가져온 목적
- 메인 프로젝트 내 위치
- 원본과 다르게 조정한 점

## 4. 구현 원칙

- 구현 언어는 **Python**으로 확정한다.
- 콘솔(CLI)에서 실행하고 사용하는 것을 최종 형태로 한다.
- 핵심 도메인 로직은 콘솔 입출력과 분리한다.
- 주문 상태 흐름은 `RESERVED -> PRODUCING -> CONFIRMED -> RELEASE` 또는
  `RESERVED -> CONFIRMED -> RELEASE`를 따른다. 상태값 표기는 `RELEASE`로 통일한다
  (`RELEASED`를 쓰지 않는다).
- `REJECTED`는 거절 상태이며 정상 모니터링 합계에서 제외한다.
- 생산 라인은 단일 라인이며 생산 큐는 FIFO다.
- 승인 판단은 raw 재고가 아니라 **가용재고**(= 재고 - 다른 미출고 주문 합계, SPEC.md
  5.1)로 한다. 먼저 승인된 주문이 재고에 우선권을 가지며, 이 계산으로 여러 주문이
  같은 재고를 중복 확정(overbooking)받는 상황을 막는다.
- 재고 부족 시 실제 생산량은 `ceil(부족분 / 수율)`로 계산한다(부족분은 가용재고 기준).
  부족분 외에 별도의 안전재고(버퍼)는 추가하지 않는다 — 이 수식이 이미 수율 손실을
  보정한 최종 생산량이다.
- 생산 완료는 담당자의 명령으로 트리거하되, 판정은 실제 경과 시간(`작업 시작 시각`
  대비 `총생산시간`)에 근거한다. 부분 생산량이라는 개념은 두지 않는다(원자적 완료).
  시간 소스는 테스트에서 mocking 가능하도록 분리한다.
- 시료 ID는 `S-001`, 주문 ID는 `ORD-YYYYMMDD-0000`(날짜 + 4자리 일련번호) 형식을 쓴다.
- 메인 메뉴는 시료관리 / 시료주문(접수) / 주문 승인·거절 / 모니터링 / 생산라인 조회 /
  출고처리 / 종료의 6+1 항목 구성을 따른다 (주문 접수와 승인·거절을 분리한다).
- 콘솔 출력은 상태 배지 등에 ANSI 컬러를 사용하고, 목록이 길어지면 PDF 데모처럼
  페이지네이션(`...외 N종, [N] 다음페이지`)을 적용한다.
- 더미/시드 데이터는 프로그램 자동 적재가 아니라 명시적 명령/옵션으로만 넣는다.
- 불필요한 DB, 웹 서버, GUI, 외부 서비스는 추가하지 않는다.

## 5. 커밋 규칙

커밋 제목은 영어로 작성한다.

권장 태그:

- `docs:` 문서 작성/수정
- `test:` 실패 테스트 또는 테스트 보강
- `feat:` 사용자-visible 기능 구현
- `fix:` 버그 수정
- `refactor:` 동작 변경 없는 구조 개선
- `chore:` 설정, 실행 환경, 정리

예시:

```text
docs: define order lifecycle specification
test: add approval scenario for insufficient stock
feat: approve orders into production queue when stock is short
```

## 6. Plan/Result 문서 규칙

- `ai-action`은 Phase 착수 전에 `docs/tasks/yyyy-mm-dd_<phase-summary>_plan.md`를
  작성한다. Test Verify와 Compliance Verify를 모두 마친 뒤에는
  `docs/tasks/yyyy-mm-dd_<phase-summary>_result.md`를 작성한다.
- `docs/PRD.md`/`docs/SPEC.md`/`docs/PLAN.md`(전체 프로젝트의 단일 진실 소스)와
  구분하기 위해, Phase별 plan/result는 반드시 `docs/tasks/` 하위에 둔다 (`docs/` 바로
  아래에 두지 않는다).
- plan/result 문서 본문은 한국어로 작성하고, 기술 용어는 원어를 유지해도 된다.
- 코드 변경이 없는 작업(문서 논의, PRD/SPEC/PLAN 자체 수정)은 plan/result 문서를
  만들지 않는다.

## 7. 테스트 규칙

- 비즈니스 로직은 테스트를 먼저 작성한다.
- 콘솔 UI보다 도메인 서비스, 상태 전이, 저장소, 생산 큐 계산을 우선 테스트한다.
- 기본 테스트 명령은 프로젝트 언어와 도구 확정 후 `README.md`와 `docs/PLAN.md`에 기록한다.
- 테스트 데이터는 직접 작성하거나 DummyDataGenerator PoC의 구조를 참고해 seed로 만든다.

## 8. 완료 기준

- 시료 등록/조회/검색이 가능하다.
- 주문 접수/승인/거절이 가능하다.
- 재고 충분 주문은 `CONFIRMED`로 전환된다.
- 재고 부족 주문은 `PRODUCING`으로 전환되고 FIFO 생산 큐에 들어간다.
- 생산 완료 후 주문이 `CONFIRMED`가 되고 재고가 반영된다.
- `CONFIRMED` 주문은 출고 처리 후 `RELEASE`가 된다.
- 모니터링에서 상태별 주문 수와 시료별 재고 상태를 확인할 수 있다.
- 프로그램을 다시 실행해도 필요한 데이터가 유지된다.
- 메인 repo 단독으로 실행 가능하다.
