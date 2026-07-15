from datetime import datetime

from sample_order.seed import build_seed_data


def fixed_now():
    return datetime(2026, 7, 15, 9, 0, 0)


def test_build_seed_data_generates_requested_counts():
    data = build_seed_data(sample_count=5, order_count=20, seed=42, now=fixed_now)

    assert len(data["samples"]) == 5
    assert len(data["orders"]) == 20


def test_build_seed_data_is_reproducible_with_same_seed():
    first = build_seed_data(sample_count=5, order_count=20, seed=42, now=fixed_now)
    second = build_seed_data(sample_count=5, order_count=20, seed=42, now=fixed_now)

    assert first == second


def test_build_seed_data_orders_reference_existing_samples():
    data = build_seed_data(sample_count=5, order_count=20, seed=7, now=fixed_now)

    sample_ids = {sample["sample_id"] for sample in data["samples"]}
    for order in data["orders"]:
        assert order["sample_id"] in sample_ids


def test_build_seed_data_production_jobs_only_for_producing_orders():
    data = build_seed_data(sample_count=5, order_count=20, seed=7, now=fixed_now)

    producing_order_ids = {
        order["order_id"] for order in data["orders"] if order["status"] == "PRODUCING"
    }
    for job in data["production_jobs"]:
        assert job["order_id"] in producing_order_ids
