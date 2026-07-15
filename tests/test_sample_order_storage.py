import json

import pytest

from sample_order.storage import StorageError, load, save


def test_load_returns_empty_schema_when_file_missing(tmp_path):
    path = tmp_path / "missing.json"

    data = load(path)

    assert data == {"samples": [], "orders": [], "production_jobs": []}


def test_save_then_load_round_trips_data(tmp_path):
    path = tmp_path / "data.json"
    data = {
        "samples": [
            {
                "sample_id": "S-001",
                "name": "Logic Sample",
                "average_production_time": 5,
                "yield_rate": 0.9,
                "stock": 3,
            }
        ],
        "orders": [],
        "production_jobs": [],
    }

    save(path, data)
    loaded = load(path)

    assert loaded == data


def test_save_writes_human_readable_json(tmp_path):
    path = tmp_path / "data.json"

    save(path, {"samples": [], "orders": [], "production_jobs": []})

    raw = path.read_text(encoding="utf-8")
    assert json.loads(raw) == {"samples": [], "orders": [], "production_jobs": []}
    assert "\n" in raw  # indented, not a single line


def test_load_missing_top_level_keys_are_backfilled_with_empty_lists(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"samples": []}), encoding="utf-8")

    data = load(path)

    assert data == {"samples": [], "orders": [], "production_jobs": []}


def test_load_raises_storage_error_with_path_on_broken_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json", encoding="utf-8")

    with pytest.raises(StorageError) as exc_info:
        load(path)

    assert str(path) in str(exc_info.value)
