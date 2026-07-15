import re
from datetime import datetime

import pytest

from sample_order.domain import Sample
from sample_order.services import (
    DuplicateSampleError,
    OrderService,
    SampleService,
    UnknownSampleError,
)


def make_sample(sample_id="S-001", name="실리콘 웨이퍼-8인치"):
    return Sample(
        sample_id=sample_id,
        name=name,
        average_production_time=0.5,
        yield_rate=0.92,
        stock=480,
    )


def test_registered_sample_is_listed():
    service = SampleService()
    service.register(make_sample())

    ids = [sample.sample_id for sample in service.list_all()]

    assert "S-001" in ids


def test_search_finds_sample_by_name_keyword():
    service = SampleService()
    service.register(make_sample(sample_id="S-001", name="실리콘 웨이퍼-8인치"))
    service.register(make_sample(sample_id="S-002", name="GaN 에피택셜-4인치"))

    results = service.search("웨이퍼")

    assert [sample.sample_id for sample in results] == ["S-001"]


def test_duplicate_sample_id_is_rejected():
    service = SampleService()
    service.register(make_sample(sample_id="S-001"))

    with pytest.raises(DuplicateSampleError):
        service.register(make_sample(sample_id="S-001"))


def fixed_now():
    return datetime(2026, 7, 15, 9, 0, 0)


def make_sample_service_with_s001():
    service = SampleService()
    service.register(make_sample())
    return service


def test_placing_an_order_creates_a_reserved_order_with_formatted_id():
    sample_service = make_sample_service_with_s001()
    order_service = OrderService(sample_service, now=fixed_now)

    order = order_service.place_order(
        sample_id="S-001", customer_name="삼성전자 파운드리", quantity=200
    )

    assert order.status == "RESERVED"
    assert order.sample_id == "S-001"
    assert order.customer_name == "삼성전자 파운드리"
    assert order.quantity == 200
    assert re.fullmatch(r"ORD-\d{8}-\d{4}", order.order_id)
    assert order.order_id == "ORD-20260715-0001"
    assert order in order_service.list_all()


def test_placing_an_order_for_unknown_sample_fails():
    sample_service = make_sample_service_with_s001()
    order_service = OrderService(sample_service, now=fixed_now)

    with pytest.raises(UnknownSampleError):
        order_service.place_order(
            sample_id="S-999", customer_name="삼성전자 파운드리", quantity=200
        )

    assert order_service.list_all() == []
