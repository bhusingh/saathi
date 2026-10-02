"""Immutable domain models shared by collectors and formatters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class Item:
    """A single source-backed fact candidate."""

    title: str
    url: str
    source: str
    published_at: datetime | None = None
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    dedupe_key: str | None = None


@dataclass(frozen=True, slots=True)
class SourceError:
    """A recoverable source failure shown in a data sheet."""

    source: str
    reason: str


@dataclass(frozen=True, slots=True)
class Sheet:
    """Normalized collector output consumed by Hermes or delivered verbatim."""

    title: str
    generated_at: datetime
    sections: tuple[tuple[str, tuple[Item, ...]], ...] = ()
    errors: tuple[SourceError, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PriceChange:
    """Latest market price and percentage change from the prior close."""

    symbol: str
    price: float
    percent: float


@dataclass(frozen=True, slots=True)
class Alert:
    """A threshold crossing safe to deliver to a notifier."""

    key: str
    message: str


@dataclass(frozen=True, slots=True)
class JobSpec:
    """Declarative Hermes scheduled-job definition."""

    name: str
    schedule: str
    collector: str | None
    prompt_file: str | None
    channel: str
    agent: bool = True
    command: tuple[str, ...] = ()
