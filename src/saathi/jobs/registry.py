"""Collector registry and dependency-injected job composition."""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

from saathi.adapters.state_json import DedupeStore
from saathi.domain.config import ConfigError, require_list, require_mapping, required_string
from saathi.domain.ports import Clock, HttpClient, StateStore
from saathi.jobs.base import CollectionJob
from saathi.jobs.sources import build_source

JobBuilder = Callable[[str, dict[str, Any], HttpClient, StateStore, Clock], CollectionJob]
JOB_TYPES: dict[str, JobBuilder] = {}


def job_type(name: str) -> Callable[[JobBuilder], JobBuilder]:
    """Register a collector type available to configuration and CLI validation."""

    def decorate(builder: JobBuilder) -> JobBuilder:
        JOB_TYPES[name] = builder
        return builder

    return decorate


@job_type("news_digest")
@job_type("github_trending")
@job_type("creator_radar")
@job_type("industry_signals")
@job_type("recalls")
@job_type("policy_watch")
@job_type("digest")
@job_type("weekly")
def build_collection(
    name: str,
    row: dict[str, Any],
    http: HttpClient,
    state: StateStore,
    clock: Clock,
) -> CollectionJob:
    """Build a standard isolated, deduplicated collection job."""

    source_rows = require_list(row.get("sources"), f"collectors.{name}.sources")
    sources = [
        build_source(require_mapping(value, f"collectors.{name}.sources"), http, state, clock)
        for value in source_rows
    ]
    title = str(row.get("title") or name.replace("_", " ").title())
    notes = ("Rules: cite every claim; skip anything that cannot be cited.",)
    dedupe = None if row.get("type") in {"digest", "weekly"} else DedupeStore(state, name, clock)
    return CollectionJob(title, sources, clock, dedupe, notes)


def build_job(
    name: str,
    collectors: dict[str, Any],
    http: HttpClient,
    state: StateStore,
    clock: Clock,
) -> CollectionJob:
    """Validate a collector name and compose it from registered dependencies."""

    if name not in collectors:
        raise ConfigError(f"unknown collector: {name}")
    row = require_mapping(collectors[name], f"collectors.{name}")
    kind = required_string(row, "type", f"collectors.{name}")
    if kind == "topic_rotation" and kind not in JOB_TYPES:
        import_module("saathi.jobs.topic_rotation")
    try:
        builder = JOB_TYPES[kind]
    except KeyError as exc:
        raise ConfigError(f"unknown collector type: {kind}") from exc
    return builder(name, row, http, state, clock)


def collector_names(collectors: dict[str, Any]) -> set[str]:
    """Return the only values accepted by ``saathi collect``."""

    return set(collectors)
