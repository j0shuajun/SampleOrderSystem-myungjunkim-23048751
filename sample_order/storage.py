"""Pure JSON file I/O for the sample order data store. No domain knowledge here."""

import json
import os

EMPTY_DATA = {"samples": [], "orders": [], "production_jobs": []}


class StorageError(Exception):
    """Raised when the data file exists but cannot be parsed as JSON."""


def load(path):
    """Load the data file at path.

    Returns a fresh copy of EMPTY_DATA when the file does not exist. Missing
    top-level keys in an otherwise valid file are backfilled with empty lists.
    Raises StorageError (with the path in the message) if the file content is
    not valid JSON.
    """
    if not os.path.exists(path):
        return {key: list(value) for key, value in EMPTY_DATA.items()}

    with open(path, encoding="utf-8") as f:
        raw = f.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StorageError(f"데이터 파일을 읽을 수 없습니다 ({path}): {exc}") from exc

    for key, default in EMPTY_DATA.items():
        data.setdefault(key, list(default))
    return data


def save(path, data):
    """Write data to path as human-readable, UTF-8 JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
