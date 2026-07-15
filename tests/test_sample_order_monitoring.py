"""Tests for read-only monitoring aggregation (Phase 7)."""

from sample_order.domain import Order, Sample
from sample_order.monitoring import MonitoringService
from sample_order.services import OrderService, SampleService


def _make_sample_service(samples):
    service = SampleService()
    for sample in samples:
        service.register(sample)
    return service


def _make_order_service_with_orders(sample_service, orders):
    order_service = OrderService(sample_service)
    order_service._orders = list(orders)
    return order_service


def test_order_status_counts_excludes_rejected():
    sample_service = _make_sample_service(
        [Sample("S-001", "Sample A", 1.0, 0.9, 100)]
    )
    orders = [
        Order("ORD-20260715-0001", "S-001", "Customer A", 1, "RESERVED"),
        Order("ORD-20260715-0002", "S-001", "Customer B", 1, "RESERVED"),
        Order("ORD-20260715-0003", "S-001", "Customer C", 1, "PRODUCING"),
        Order("ORD-20260715-0004", "S-001", "Customer D", 1, "CONFIRMED"),
        Order("ORD-20260715-0005", "S-001", "Customer E", 1, "RELEASE"),
        Order("ORD-20260715-0006", "S-001", "Customer F", 1, "REJECTED"),
    ]
    order_service = _make_order_service_with_orders(sample_service, orders)
    monitoring = MonitoringService(sample_service, order_service)

    counts = monitoring.order_status_counts()

    assert counts == {
        "RESERVED": 2,
        "PRODUCING": 1,
        "CONFIRMED": 1,
        "RELEASE": 1,
    }
    assert "REJECTED" not in counts
    assert monitoring.rejected_count() == 1


def test_inventory_status_classifies_ample_shortage_and_depleted():
    samples = [
        Sample("S-001", "Sample A", 1.0, 0.9, 20),
        Sample("S-002", "Sample B", 1.0, 0.9, 5),
        Sample("S-003", "Sample C", 1.0, 0.9, 0),
    ]
    sample_service = _make_sample_service(samples)
    orders = [
        Order("ORD-20260715-0001", "S-001", "Customer A", 5, "RESERVED"),
        Order("ORD-20260715-0002", "S-001", "Customer B", 10, "PRODUCING"),
        Order("ORD-20260715-0003", "S-001", "Customer C", 3, "CONFIRMED"),
        Order("ORD-20260715-0004", "S-001", "Customer D", 7, "RELEASE"),
        Order("ORD-20260715-0005", "S-002", "Customer E", 3, "RESERVED"),
        Order("ORD-20260715-0006", "S-002", "Customer F", 5, "PRODUCING"),
    ]
    order_service = _make_order_service_with_orders(sample_service, orders)
    monitoring = MonitoringService(sample_service, order_service)

    results = {item.sample_id: item for item in monitoring.inventory_status()}

    assert results["S-001"].stock == 20
    assert results["S-001"].unshipped_quantity == 18
    assert results["S-001"].state == "여유"

    assert results["S-002"].stock == 5
    assert results["S-002"].unshipped_quantity == 8
    assert results["S-002"].state == "부족"

    assert results["S-003"].stock == 0
    assert results["S-003"].unshipped_quantity == 0
    assert results["S-003"].state == "고갈"
