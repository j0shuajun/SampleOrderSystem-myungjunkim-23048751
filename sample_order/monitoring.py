"""Read-only monitoring aggregation. No console input/output belongs here.

MonitoringService only reads from SampleService/OrderService via their public
list_all() methods; it never mutates order or sample state (that remains the
responsibility of the Phase 1-6 services).
"""

from dataclasses import dataclass

# Statuses counted as normal operational states. REJECTED is intentionally
# excluded (see SPEC.md 4/8 - rejected orders are excluded from normal
# monitoring totals) and exposed only via rejected_count().
ORDER_STATUSES = ("RESERVED", "PRODUCING", "CONFIRMED", "RELEASE")

# Statuses that still represent stock owed to a customer (not yet shipped).
UNSHIPPED_STATUSES = ("RESERVED", "PRODUCING", "CONFIRMED")

STATE_DEPLETED = "고갈"
STATE_AMPLE = "여유"
STATE_SHORTAGE = "부족"


@dataclass
class InventoryStatus:
    sample_id: str
    name: str
    stock: int
    unshipped_quantity: int
    state: str


class MonitoringService:
    """Aggregates order/sample state across the system for reporting."""

    def __init__(self, sample_service, order_service):
        self._sample_service = sample_service
        self._order_service = order_service

    def order_status_counts(self):
        counts = {status: 0 for status in ORDER_STATUSES}
        for order in self._order_service.list_all():
            if order.status in counts:
                counts[order.status] += 1
        return counts

    def rejected_count(self):
        return sum(
            1 for order in self._order_service.list_all() if order.status == "REJECTED"
        )

    def inventory_status(self):
        orders = self._order_service.list_all()
        results = []
        for sample in self._sample_service.list_all():
            unshipped_quantity = sum(
                order.quantity
                for order in orders
                if order.sample_id == sample.sample_id
                and order.status in UNSHIPPED_STATUSES
            )
            state = self._classify(sample.stock, unshipped_quantity)
            results.append(
                InventoryStatus(
                    sample_id=sample.sample_id,
                    name=sample.name,
                    stock=sample.stock,
                    unshipped_quantity=unshipped_quantity,
                    state=state,
                )
            )
        return results

    @staticmethod
    def _classify(stock, unshipped_quantity):
        # Depleted takes priority even when unshipped demand is zero
        # (SPEC.md 8 boundary case: stock == 0 and unshipped == 0 -> depleted).
        if stock == 0:
            return STATE_DEPLETED
        if stock >= unshipped_quantity:
            return STATE_AMPLE
        return STATE_SHORTAGE
