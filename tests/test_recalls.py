from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from saathi.adapters.openfda import OpenFdaRecallSource, is_animal_product
from saathi.adapters.state_json import DedupeStore, JsonStateStore
from saathi.jobs.base import CollectionJob


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 5, tzinfo=UTC)

    def today(self) -> date:
        return self.now().date()


class RecallHttp:
    def get(self, url: str, *, accept: str | None = None) -> bytes:
        raise AssertionError("unexpected byte request")

    def get_json(self, url: str) -> Any:
        return {
            "results": [
                {
                    "product_description": "dog food",
                    "recall_number": "R-1",
                    "recalling_firm": "One",
                },
                {
                    "product_description": "cat food",
                    "recall_number": "R-2",
                    "recalling_firm": "Two",
                },
            ]
        }


def test_animal_filter_rejects_pet_plastic() -> None:
    assert not is_animal_product("Water bottles packaged in PET plastic")


def test_animal_filter_accepts_specific_animals() -> None:
    assert is_animal_product("Frozen dog food and cat treats")
    assert is_animal_product("Canine supplement")


def test_recalls_with_shared_reference_url_use_recall_number_for_dedupe(tmp_path: Path) -> None:
    clock = FixedClock()
    source = OpenFdaRecallSource(RecallHttp(), clock)
    dedupe = DedupeStore(JsonStateStore(tmp_path), "recalls", clock)
    sheet = CollectionJob("recalls", [source], clock, dedupe).run()
    items = sheet.sections[0][1]
    assert [item.dedupe_key for item in items] == ["R-1", "R-2"]
