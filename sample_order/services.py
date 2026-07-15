"""Sample and order services. No console input/output here."""

import re
from datetime import datetime

from sample_order.domain import Order

_ORDER_ID_PATTERN = re.compile(r"^ORD-(\d{8})-(\d+)$")


class DuplicateSampleError(Exception):
    """Raised when registering a sample_id that already exists."""


class UnknownSampleError(Exception):
    """Raised when an order references a sample_id that was never registered."""


class InvalidOrderStateError(Exception):
    """Raised when approving/rejecting an order that is not RESERVED."""


class InsufficientStockError(Exception):
    """Raised when releasing an order but stock is not enough (defensive check)."""


COMMITTED_STATUSES = ("PRODUCING", "CONFIRMED")


class SampleService:
    def __init__(self):
        self._samples = []

    def register(self, sample):
        if any(s.sample_id == sample.sample_id for s in self._samples):
            raise DuplicateSampleError(f"이미 등록된 시료 ID입니다: {sample.sample_id}")
        self._samples.append(sample)
        return sample

    def list_all(self):
        return list(self._samples)

    def search(self, keyword):
        return [s for s in self._samples if keyword in s.name or keyword in s.sample_id]

    def exists(self, sample_id):
        return any(s.sample_id == sample_id for s in self._samples)

    def find(self, sample_id):
        for s in self._samples:
            if s.sample_id == sample_id:
                return s
        return None

    def replace_all(self, samples):
        """Restore the full sample list from persisted storage (no dup check)."""
        self._samples = list(samples)


class OrderService:
    def __init__(self, sample_service, now=datetime.now, production_line=None):
        self._sample_service = sample_service
        self._now = now
        self._production_line = production_line
        self._orders = []
        self._daily_sequence = {}

    def _next_order_id(self):
        date_str = self._now().strftime("%Y%m%d")
        sequence = self._daily_sequence.get(date_str, 0) + 1
        self._daily_sequence[date_str] = sequence
        return f"ORD-{date_str}-{sequence:04d}"

    def place_order(self, sample_id, customer_name, quantity):
        if not self._sample_service.exists(sample_id):
            raise UnknownSampleError(f"등록되지 않은 시료 ID입니다: {sample_id}")
        order = Order(
            order_id=self._next_order_id(),
            sample_id=sample_id,
            customer_name=customer_name,
            quantity=quantity,
            status="RESERVED",
        )
        self._orders.append(order)
        return order

    def list_all(self):
        return list(self._orders)

    def _find_order(self, order_id):
        for order in self._orders:
            if order.order_id == order_id:
                return order
        return None

    def _available_stock(self, sample_id, excluding_order_id):
        sample = self._sample_service.find(sample_id)
        committed = sum(
            order.quantity
            for order in self._orders
            if order.sample_id == sample_id
            and order.order_id != excluding_order_id
            and order.status in COMMITTED_STATUSES
        )
        return max(0, sample.stock - committed)

    def _require_reserved(self, order_id):
        order = self._find_order(order_id)
        if order is None or order.status != "RESERVED":
            raise InvalidOrderStateError(
                f"RESERVED 상태의 주문만 승인/거절할 수 있습니다: {order_id}"
            )
        return order

    def approve(self, order_id):
        order = self._require_reserved(order_id)
        available = self._available_stock(order.sample_id, excluding_order_id=order_id)
        if available >= order.quantity:
            order.status = "CONFIRMED"
        else:
            order.status = "PRODUCING"
            if self._production_line is not None:
                sample = self._sample_service.find(order.sample_id)
                shortage = order.quantity - available
                self._production_line.enqueue(order, sample, shortage)
        return order

    def mark_confirmed(self, order_id):
        order = self._find_order(order_id)
        if order is None or order.status != "PRODUCING":
            raise InvalidOrderStateError(
                f"PRODUCING 상태의 주문만 생산 완료로 CONFIRMED될 수 있습니다: {order_id}"
            )
        order.status = "CONFIRMED"
        return order

    def reject(self, order_id):
        order = self._require_reserved(order_id)
        order.status = "REJECTED"
        return order

    def release(self, order_id):
        order = self._find_order(order_id)
        if order is None or order.status != "CONFIRMED":
            raise InvalidOrderStateError(
                f"CONFIRMED 상태의 주문만 출고할 수 있습니다: {order_id}"
            )
        sample = self._sample_service.find(order.sample_id)
        if sample.stock < order.quantity:
            raise InsufficientStockError(
                f"재고가 부족해 출고할 수 없습니다: {order_id}"
            )
        sample.stock -= order.quantity
        order.status = "RELEASE"
        return order

    def replace_all(self, orders):
        """Restore the full order list and recompute the daily sequence counters
        from existing order_ids (ORD-YYYYMMDD-NNNN) so future IDs do not collide."""
        self._orders = list(orders)
        self._daily_sequence = {}
        for order in self._orders:
            match = _ORDER_ID_PATTERN.match(order.order_id)
            if match is None:
                continue
            date_str, sequence_str = match.groups()
            sequence = int(sequence_str)
            if sequence > self._daily_sequence.get(date_str, 0):
                self._daily_sequence[date_str] = sequence
