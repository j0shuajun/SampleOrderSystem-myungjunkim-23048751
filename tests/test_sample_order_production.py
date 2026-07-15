from datetime import datetime, timedelta

import pytest

from sample_order.domain import Order, Sample
from sample_order.production import ProductionLine, ProductionNotYetCompleteError
from sample_order.services import OrderService, SampleService


def make_sample(sample_id="S-003", yield_rate=0.92):
    return Sample(
        sample_id=sample_id,
        name="SiC 파워기판-6인치",
        average_production_time=0.8,
        yield_rate=yield_rate,
        stock=70,
    )


def make_order(order_id, sample_id="S-003", quantity=200):
    return Order(
        order_id=order_id,
        sample_id=sample_id,
        customer_name="삼성전자 파운드리",
        quantity=quantity,
        status="PRODUCING",
    )


def test_enqueue_computes_planned_quantity_from_shortage_and_yield():
    line = ProductionLine()
    sample = make_sample(yield_rate=0.92)
    order = make_order("ORD-20260715-0001")

    job = line.enqueue(order, sample, shortage=130)

    assert job.shortage == 130
    assert job.planned_quantity == 142  # ceil(130 / 0.92) == 142
    assert job.status == "QUEUED"
    assert job.started_at is None


def test_queue_returns_jobs_in_fifo_order():
    line = ProductionLine()
    sample = make_sample()

    first = line.enqueue(make_order("ORD-20260715-0001"), sample, shortage=30)
    second = line.enqueue(make_order("ORD-20260715-0002"), sample, shortage=50)
    third = line.enqueue(make_order("ORD-20260715-0003"), sample, shortage=10)

    queue = line.list_queue()

    assert [job.order_id for job in queue] == [
        first.order_id,
        second.order_id,
        third.order_id,
    ]


def make_full_pipeline():
    """S-003(평균생산시간 0.8분, 수율 0.92, 재고 70)에 200개 주문을 승인해
    부족분 130 -> 계획생산량 142인 작업을 큐에 만들어 둔 상태를 준비한다."""
    sample_service = SampleService()
    sample_service.register(make_sample())
    production_line = ProductionLine()
    order_service = OrderService(
        sample_service, now=lambda: datetime(2026, 7, 15, 9, 0, 0), production_line=production_line
    )
    order = order_service.place_order(
        sample_id="S-003", customer_name="삼성전자 파운드리", quantity=200
    )
    order_service.approve(order.order_id)
    return sample_service, order_service, production_line, order


def test_start_next_marks_job_in_progress_and_records_start_time():
    sample_service, order_service, line, order = make_full_pipeline()
    start_time = datetime(2026, 7, 15, 9, 0, 0)

    job = line.start_next(now=lambda: start_time)

    assert job.status == "IN_PROGRESS"
    assert job.started_at == start_time
    assert line.list_queue() == []  # 진행 중인 작업은 대기 큐에 더 이상 없음


def test_start_next_fails_while_another_job_is_in_progress():
    sample_service, order_service, line, order = make_full_pipeline()
    line.start_next(now=lambda: datetime(2026, 7, 15, 9, 0, 0))

    with pytest.raises(Exception):
        line.start_next(now=lambda: datetime(2026, 7, 15, 9, 5, 0))


def test_completing_before_total_production_time_is_rejected():
    sample_service, order_service, line, order = make_full_pipeline()
    line.start_next(now=lambda: datetime(2026, 7, 15, 9, 0, 0))
    # 총생산시간 = 0.8 * 142 = 113.6분. 60분만 지남 -> 아직 부족.
    too_early = datetime(2026, 7, 15, 10, 0, 0)

    with pytest.raises(ProductionNotYetCompleteError):
        line.complete_current(now=lambda: too_early, sample_service=sample_service, order_service=order_service)

    sample = sample_service.find("S-003")
    assert sample.stock == 70  # 재고 불변
    assert order.status == "PRODUCING"  # 주문 상태 불변


def test_completing_after_total_production_time_confirms_order_and_restocks():
    sample_service, order_service, line, order = make_full_pipeline()
    line.start_next(now=lambda: datetime(2026, 7, 15, 9, 0, 0))
    # 113.6분보다 더 지난 시각(120분 후)
    enough_time = datetime(2026, 7, 15, 9, 0, 0) + timedelta(minutes=120)

    line.complete_current(now=lambda: enough_time, sample_service=sample_service, order_service=order_service)

    sample = sample_service.find("S-003")
    assert sample.stock == 70 + 130  # floor(142 * 0.92) == 130
    assert order.status == "CONFIRMED"
