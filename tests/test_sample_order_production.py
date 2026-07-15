from sample_order.domain import Order, Sample
from sample_order.production import ProductionLine


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
