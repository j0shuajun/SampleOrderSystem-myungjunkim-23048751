# Phase 5: 생산 완료 — 결과

Written at (KST): 2026-07-15 16:30

## 1. 한눈에 보는 요약

생산 큐의 작업을 시작하면 시작 시각이 기록되고, 총생산시간이 지나야만 완료 처리로
재고가 늘고 주문이 `CONFIRMED`가 된다. 단일 라인이라 동시에 두 작업을 진행할 수
없다.

## 2. 왜 필요했는지

지난 Phase까지는 "얼마나 생산해야 하는지"만 계산했고, "생산이 끝났다"를 판단하는
기준이 없었다. PDF의 "생산완료 처리" 메뉴와 SPEC.md의 시간 기반 완료 판정을
실제로 동작하게 만드는 단계다.

## 3. 예시로 보는 결과

계획생산량 142(평균생산시간 0.8분) 작업 → 총생산시간 113.6분.

- 시작 후 60분 시점에 완료 시도 → "아직 생산이 끝나지 않았습니다. 남은 시간:
  53.6분" 거부. 재고·주문 상태 그대로.
- 시작 후 120분 시점에 완료 시도 → 재고 `70 + floor(142×0.92)=70+130=200`,
  주문 `CONFIRMED`.
- 경계 검증: 정확히 총생산시간만큼 지난 시점도 완료로 인정됨을 별도 스크립트로
  확인.

## 4. 변경 내용

- `sample_order/production.py`: `start_next`, `complete_current`,
  `ProductionNotYetCompleteError`, `ProductionInProgressError`,
  `NoJobInProgressError`
- `sample_order/services.py`: `OrderService.mark_confirmed`(PRODUCING 주문을
  생산완료로 CONFIRMED 전환)

## 5. 검증 결과

- Test Verify: `pytest -q` → 20 passed. 추가로 경계 시각(경과시간==총생산시간)
  시나리오를 직접 실행해 `>=` 비교가 올바르게 동작함을 확인. PASS
- Compliance Verify: PLAN.md Phase 5 요구사항 6항목 모두 Satisfied. PASS

## 6. 영향 범위

Phase 6(출고 처리)이 이제 `CONFIRMED`가 된 주문을 대상으로 동작한다.

## 7. 제약/후속

- 출고 처리(재고 차감, `RELEASE` 전환)는 Phase 6에서 다룬다.
- 콘솔에서 "생산완료 처리" 명령을 눌렀을 때의 안내 문구(rich 렌더링)는 Phase 9로
  미룬다 — 지금은 예외 메시지 텍스트로만 존재한다.

## 8. Lessons

"생산된 정상 시료 수량"이 계획생산량 그 자체인지, 수율을 다시 적용한 값인지가
SPEC.md에 명시돼 있지 않아 doc-consistency-verifier 단계에서 FAIL로 잡아 사용자
확인을 받았다. `총생산시간 = 평균생산시간 × 계획생산량` 공식이 이미 성립하려면
`평균생산시간`이 "시도 1건당" 시간이어야 하고, 따라서 `계획생산량`은 raw 시도
횟수라는 점을 근거로 들어 모호함을 좁혔다 — 앞으로도 서로 다른 공식이 같은
변수를 다른 의미로 쓰고 있지 않은지 계산식끼리 교차 검증하는 습관이 유용하다.
