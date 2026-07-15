from sample_order.domain import Sample


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
