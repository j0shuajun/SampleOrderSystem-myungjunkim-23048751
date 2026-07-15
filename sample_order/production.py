"""Single FIFO production line. No console input/output here."""

import math
import re
from datetime import datetime

from sample_order.domain import ProductionJob

_JOB_ID_PATTERN = re.compile(r"^JOB-(\d+)$")


class ProductionNotYetCompleteError(Exception):
    """Raised when completing a job before its total production time has elapsed."""

    def __init__(self, remaining_minutes):
        self.remaining_minutes = remaining_minutes
        super().__init__(f"아직 생산이 끝나지 않았습니다. 남은 시간: {remaining_minutes:.1f}분")


class ProductionInProgressError(Exception):
    """Raised when starting a job while another one is already in progress."""


class NoJobInProgressError(Exception):
    """Raised when completing while no job is in progress."""


class ProductionLine:
    def __init__(self):
        self._jobs = []
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
        self._jobs.append(job)
        return job

    def list_queue(self):
        return [job for job in self._jobs if job.status == "QUEUED"]

    def list_all(self):
        """Return every job regardless of status (used for persistence)."""
        return list(self._jobs)

    def replace_all(self, jobs):
        """Restore the full job list and recompute the next job number from
        existing job_ids (JOB-NNNN) so future IDs do not collide."""
        self._jobs = list(jobs)
        max_number = 0
        for job in self._jobs:
            match = _JOB_ID_PATTERN.match(job.job_id)
            if match is None:
                continue
            max_number = max(max_number, int(match.group(1)))
        self._next_job_number = max_number + 1 if max_number else 1

    def _current_job(self):
        for job in self._jobs:
            if job.status == "IN_PROGRESS":
                return job
        return None

    def start_next(self, now=datetime.now):
        if self._current_job() is not None:
            raise ProductionInProgressError("이미 진행 중인 생산 작업이 있습니다.")
        queued = self.list_queue()
        if not queued:
            return None
        job = queued[0]
        job.status = "IN_PROGRESS"
        job.started_at = now()
        return job

    def complete_current(self, sample_service, order_service, now=datetime.now):
        job = self._current_job()
        if job is None:
            raise NoJobInProgressError("완료 처리할 진행 중인 생산 작업이 없습니다.")

        sample = sample_service.find(job.sample_id)
        total_minutes = sample.average_production_time * job.planned_quantity
        elapsed_minutes = (now() - job.started_at).total_seconds() / 60

        if elapsed_minutes < total_minutes:
            raise ProductionNotYetCompleteError(total_minutes - elapsed_minutes)

        produced_good_units = math.floor(job.planned_quantity * sample.yield_rate)
        sample.stock += produced_good_units
        order_service.mark_confirmed(job.order_id)
        job.status = "DONE"
        return job
