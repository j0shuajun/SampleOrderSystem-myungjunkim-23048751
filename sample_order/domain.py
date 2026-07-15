"""Core domain entities. No console input/output belongs here."""

from dataclasses import dataclass


@dataclass
class Sample:
    sample_id: str
    name: str
    average_production_time: float
    yield_rate: float
    stock: int


@dataclass
class Order:
    order_id: str
    sample_id: str
    customer_name: str
    quantity: int
    status: str


@dataclass
class ProductionJob:
    job_id: str
    order_id: str
    sample_id: str
    shortage: int
    planned_quantity: int
    status: str
    started_at: object = None
