"""Sample and order services. No console input/output here."""

from datetime import datetime

from sample_order.domain import Order


class DuplicateSampleError(Exception):
    """Raised when registering a sample_id that already exists."""


class UnknownSampleError(Exception):
    """Raised when an order references a sample_id that was never registered."""


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


class OrderService:
    def __init__(self, sample_service, now=datetime.now):
        self._sample_service = sample_service
        self._now = now
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
