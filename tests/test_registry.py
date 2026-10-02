from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from saathi.adapters.state_json import JsonStateStore
from saathi.domain.config import ConfigError
from saathi.domain.models import Item
from saathi.jobs.base import CollectionJob
from saathi.jobs.registry import JOB_TYPES, build_job
from saathi.jobs.sources import SOURCE_TYPES


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 5, tzinfo=UTC)

    def today(self) -> date:
        return self.now().date()


class FakeHttp:
    def get(self, url: str, *, accept: str | None = None) -> bytes:
        return b""

    def get_json(self, url: str) -> Any:
        return {}


class GoodSource:
    name = "good"

    def collect(self) -> list[Item]:
        return [Item("title", "https://example.com", self.name)]


class BadSource:
    name = "bad"

    def collect(self) -> list[Item]:
        raise TimeoutError


def test_registry_has_expected_plugin_types() -> None:
    assert {"news_digest", "github_trending", "recalls"} <= JOB_TYPES.keys()
    assert {"rss", "reddit", "github", "openfda"} <= SOURCE_TYPES.keys()


def test_unknown_job_is_rejected_before_execution(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="unknown collector"):
        build_job("missing", {}, FakeHttp(), JsonStateStore(tmp_path), FixedClock())


def test_source_failure_does_not_cancel_sheet() -> None:
    sheet = CollectionJob("test", [BadSource(), GoodSource()], FixedClock()).run()
    assert sheet.sections[0][0] == "good"
    assert sheet.errors[0].source == "bad"


def test_all_example_collectors_compose_without_io(tmp_path: Path) -> None:
    from saathi.domain.config import load_yaml, require_mapping

    config = load_yaml(Path(__file__).parents[1] / "config/sources.example.yaml")
    collectors = require_mapping(config["collectors"], "collectors")
    for name in collectors:
        job = build_job(name, collectors, FakeHttp(), JsonStateStore(tmp_path), FixedClock())
        assert isinstance(job, CollectionJob)
