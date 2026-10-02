"""Weekday-driven source rotation."""

from __future__ import annotations

from typing import Any

from saathi.adapters.state_json import DedupeStore
from saathi.domain.config import require_list, require_mapping
from saathi.domain.ports import Clock, HttpClient, StateStore
from saathi.jobs.base import CollectionJob
from saathi.jobs.registry import job_type
from saathi.jobs.sources import build_source


@job_type("topic_rotation")
def build_topic_rotation(
    name: str,
    row: dict[str, Any],
    http: HttpClient,
    state: StateStore,
    clock: Clock,
) -> CollectionJob:
    """Build today's configured rotation without hard-coded topics."""

    days = require_mapping(row.get("days"), f"collectors.{name}.days")
    day = days.get(str(clock.now().weekday()))
    if day is None:
        return CollectionJob("No topic scheduled today", (), clock)
    selected = require_mapping(day, f"collectors.{name}.days")
    source_rows = require_list(selected.get("sources"), f"collectors.{name}.days.sources")
    sources = [
        build_source(require_mapping(value, name), http, state, clock) for value in source_rows
    ]
    title = str(selected.get("title") or "Topic rotation")
    return CollectionJob(title, sources, clock, DedupeStore(state, name, clock))
