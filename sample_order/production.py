"""Single FIFO production line. No console input/output here."""

import math

from sample_order.domain import ProductionJob


class ProductionLine:
    def __init__(self):
        self._queue = []
        self._next_job_number = 1

    def enqueue(self, order, sample, shortage):
        planned_quantity = math.ceil(shortage / sample.yield_rate)
        job = ProductionJob(
            job_id=f"JOB-{self._next_job_number:04d}",
            order_id=order.order_id,
            sample_id=sample.sample_id,
            shortage=shortage,
            planned_quantity=planned_quantity,
            status="QUEUED",
            started_at=None,
        )
        self._next_job_number += 1
        self._queue.append(job)
        return job

    def list_queue(self):
        return list(self._queue)
