"""Core domain entities. No console input/output belongs here."""

from dataclasses import dataclass


@dataclass
class Sample:
    sample_id: str
    name: str
    average_production_time: float
    yield_rate: float
    stock: int
