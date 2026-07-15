"""Dataclass <-> dict (de)serialization and the top-level Repository facade.

Keeps JSON format knowledge out of domain.py/services.py/production.py, per
SPEC 9 (data persistence) and SPEC 13 (example JSON schema).
"""

from dataclasses import asdict
from datetime import datetime

from sample_order import storage
from sample_order.domain import Order, ProductionJob, Sample


def _sample_to_dict(sample):
    return asdict(sample)


def _sample_from_dict(data):
    return Sample(**data)


def _order_to_dict(order):
    return asdict(order)


def _order_from_dict(data):
    return Order(**data)


def _job_to_dict(job):
    data = asdict(job)
    data["started_at"] = job.started_at.isoformat() if job.started_at else None
    return data


def _job_from_dict(data):
    data = dict(data)
    started_at = data.get("started_at")
    data["started_at"] = datetime.fromisoformat(started_at) if started_at else None
    return ProductionJob(**data)


class Repository:
    """Persists and restores the full state of the sample order services."""

    def __init__(self, path="data.json"):
        self.path = path

    def save(self, sample_service, order_service, production_line):
        data = {
            "samples": [_sample_to_dict(s) for s in sample_service.list_all()],
            "orders": [_order_to_dict(o) for o in order_service.list_all()],
            "production_jobs": [_job_to_dict(j) for j in production_line.list_all()],
        }
        storage.save(self.path, data)

    def load_into(self, sample_service, order_service, production_line):
        data = storage.load(self.path)
        sample_service.replace_all([_sample_from_dict(s) for s in data["samples"]])
        order_service.replace_all([_order_from_dict(o) for o in data["orders"]])
        production_line.replace_all(
            [_job_from_dict(j) for j in data["production_jobs"]]
        )
