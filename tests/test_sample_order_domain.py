from sample_order.domain import Order, Sample


def test_sample_holds_its_fields():
    sample = Sample(
        sample_id="S-001",
        name="실리콘 웨이퍼-8인치",
        average_production_time=0.5,
        yield_rate=0.92,
        stock=480,
    )

    assert sample.sample_id == "S-001"
    assert sample.name == "실리콘 웨이퍼-8인치"
    assert sample.average_production_time == 0.5
    assert sample.yield_rate == 0.92
    assert sample.stock == 480


def test_order_holds_its_fields():
    order = Order(
        order_id="ORD-20260715-0001",
        sample_id="S-001",
        customer_name="삼성전자 파운드리",
        quantity=200,
        status="RESERVED",
    )

    assert order.order_id == "ORD-20260715-0001"
    assert order.sample_id == "S-001"
    assert order.customer_name == "삼성전자 파운드리"
    assert order.quantity == 200
    assert order.status == "RESERVED"
