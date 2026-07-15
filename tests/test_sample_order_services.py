import pytest

from sample_order.domain import Sample
from sample_order.services import DuplicateSampleError, SampleService


def make_sample(sample_id="S-001", name="실리콘 웨이퍼-8인치"):
    return Sample(
        sample_id=sample_id,
        name=name,
        average_production_time=0.5,
        yield_rate=0.92,
        stock=480,
    )


def test_registered_sample_is_listed():
    service = SampleService()
    service.register(make_sample())

    ids = [sample.sample_id for sample in service.list_all()]

    assert "S-001" in ids


def test_search_finds_sample_by_name_keyword():
    service = SampleService()
    service.register(make_sample(sample_id="S-001", name="실리콘 웨이퍼-8인치"))
    service.register(make_sample(sample_id="S-002", name="GaN 에피택셜-4인치"))

    results = service.search("웨이퍼")

    assert [sample.sample_id for sample in results] == ["S-001"]


def test_duplicate_sample_id_is_rejected():
    service = SampleService()
    service.register(make_sample(sample_id="S-001"))

    with pytest.raises(DuplicateSampleError):
        service.register(make_sample(sample_id="S-001"))
