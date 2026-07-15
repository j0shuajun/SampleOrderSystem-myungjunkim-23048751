import json
from datetime import datetime

from sample_order.domain import Sample
from sample_order.production import ProductionLine
from sample_order.repository import Repository
from sample_order.services import OrderService, SampleService


def make_pipeline(now):
    """Builds the SPEC 13 example state: S-001 stock 3, order for 10 approved
    while short by 7, producing JOB-0001 with planned_quantity 8 (ceil(7/0.9))."""
    sample_service = SampleService()
    sample_service.register(
        Sample(
            sample_id="S-001",
            name="Logic Sample",
            average_production_time=5,
            yield_rate=0.9,
            stock=3,
        )
    )
    production_line = ProductionLine()
    order_service = OrderService(sample_service, now=now, production_line=production_line)
    order = order_service.place_order(
        sample_id="S-001", customer_name="Fabless A", quantity=10
    )
    order_service.approve(order.order_id)
    return sample_service, order_service, production_line, order


def test_save_then_load_into_restores_samples_orders_and_jobs(tmp_path):
    now = lambda: datetime(2026, 4, 16, 9, 0, 0)
    sample_service, order_service, production_line, order = make_pipeline(now)
    repo_path = tmp_path / "data.json"
    repo = Repository(path=repo_path)

    repo.save(sample_service, order_service, production_line)

    on_disk = json.loads(repo_path.read_text(encoding="utf-8"))
    assert on_disk["samples"][0]["sample_id"] == "S-001"
    assert on_disk["orders"][0]["order_id"] == "ORD-20260416-0001"
    assert on_disk["production_jobs"][0]["job_id"] == "JOB-0001"
    assert on_disk["production_jobs"][0]["started_at"] is None

    sample_service2 = SampleService()
    order_service2 = OrderService(sample_service2, now=now)
    production_line2 = ProductionLine()
    repo.load_into(sample_service2, order_service2, production_line2)

    assert sample_service2.find("S-001").stock == 3
    restored_order = order_service2.list_all()[0]
    assert restored_order.order_id == "ORD-20260416-0001"
    assert restored_order.status == "PRODUCING"
    restored_job = production_line2.list_all()[0]
    assert restored_job.job_id == "JOB-0001"
    assert restored_job.status == "QUEUED"
    assert restored_job.shortage == 7
    assert restored_job.planned_quantity == 8
    assert restored_job.started_at is None


def test_started_at_round_trips_as_datetime_not_string(tmp_path):
    now = lambda: datetime(2026, 4, 16, 9, 0, 0)
    sample_service, order_service, production_line, order = make_pipeline(now)
    production_line.start_next(now=lambda: datetime(2026, 7, 15, 9, 0, 0))
    repo_path = tmp_path / "data.json"
    repo = Repository(path=repo_path)

    repo.save(sample_service, order_service, production_line)

    on_disk = json.loads(repo_path.read_text(encoding="utf-8"))
    assert on_disk["production_jobs"][0]["started_at"] == "2026-07-15T09:00:00"

    sample_service2 = SampleService()
    order_service2 = OrderService(sample_service2, now=now)
    production_line2 = ProductionLine()
    repo.load_into(sample_service2, order_service2, production_line2)

    restored_job = production_line2.list_all()[0]
    assert restored_job.status == "IN_PROGRESS"
    assert restored_job.started_at == datetime(2026, 7, 15, 9, 0, 0)


def test_load_into_with_missing_file_leaves_empty_services(tmp_path):
    repo = Repository(path=tmp_path / "missing.json")
    sample_service = SampleService()
    order_service = OrderService(sample_service)
    production_line = ProductionLine()

    repo.load_into(sample_service, order_service, production_line)

    assert sample_service.list_all() == []
    assert order_service.list_all() == []
    assert production_line.list_all() == []


def test_id_sequences_continue_after_restore_for_orders_and_jobs(tmp_path):
    now = lambda: datetime(2026, 4, 16, 9, 0, 0)
    sample_service, order_service, production_line, order = make_pipeline(now)
    repo_path = tmp_path / "data.json"
    repo = Repository(path=repo_path)
    repo.save(sample_service, order_service, production_line)

    sample_service2 = SampleService()
    order_service2 = OrderService(sample_service2, now=now)
    production_line2 = ProductionLine()
    repo.load_into(sample_service2, order_service2, production_line2)

    new_order = order_service2.place_order(
        sample_id="S-001", customer_name="Fabless B", quantity=5
    )
    assert new_order.order_id == "ORD-20260416-0002"

    sample = sample_service2.find("S-001")
    new_job = production_line2.enqueue(new_order, sample, shortage=2)
    assert new_job.job_id == "JOB-0002"
