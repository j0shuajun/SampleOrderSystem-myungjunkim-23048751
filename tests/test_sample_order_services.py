import re
from datetime import datetime

import pytest

from sample_order.domain import Order, Sample
from sample_order.services import (
    DuplicateSampleError,
    InvalidOrderStateError,
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


def test_approving_order_with_sufficient_available_stock_confirms_it():
    # 재고 480, 다른 미출고 주문 없음 -> 가용재고 480 >= 50
    sample_service = make_sample_service_with_s001()
    order_service = OrderService(sample_service, now=fixed_now)
    order = order_service.place_order(
        sample_id="S-001", customer_name="삼성전자 파운드리", quantity=50
    )

    order_service.approve(order.order_id)

    assert order.status == "CONFIRMED"


def test_approving_order_blocked_by_existing_producing_order_becomes_producing():
    # 재고 70, 주문 A(100)가 이미 PRODUCING(=committed 100)인 상태에서
    # 주문 B(20)를 승인하면 raw 재고(70)만 보면 충분해 보이지만
    # 가용재고 = max(0, 70 - 100) = 0 < 20 이므로 CONFIRMED가 아니라 PRODUCING.
    sample_service = SampleService()
    sample_service.register(
        Sample(
            sample_id="S-003",
            name="SiC 파워기판-6인치",
            average_production_time=0.8,
            yield_rate=0.92,
            stock=70,
        )
    )
    order_service = OrderService(sample_service, now=fixed_now)
    order_service._orders.append(
        Order(
            order_id="ORD-20260715-0001",
            sample_id="S-003",
            customer_name="LG이노텍",
            quantity=100,
            status="PRODUCING",
        )
    )
    order_b = order_service.place_order(
        sample_id="S-003", customer_name="SK하이닉스", quantity=20
    )

    order_service.approve(order_b.order_id)

    assert order_b.status == "PRODUCING"


def test_rejecting_reserved_order_marks_it_rejected():
    sample_service = make_sample_service_with_s001()
    order_service = OrderService(sample_service, now=fixed_now)
    order = order_service.place_order(
        sample_id="S-001", customer_name="삼성전자 파운드리", quantity=50
    )

    order_service.reject(order.order_id)

    assert order.status == "REJECTED"


def test_approving_a_non_reserved_order_fails():
    sample_service = make_sample_service_with_s001()
    order_service = OrderService(sample_service, now=fixed_now)
    order = order_service.place_order(
        sample_id="S-001", customer_name="삼성전자 파운드리", quantity=50
    )
    order_service.reject(order.order_id)

    with pytest.raises(InvalidOrderStateError):
        order_service.approve(order.order_id)
