"""Ports implemented by infrastructure adapters."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol

from saathi.domain.models import Item, PriceChange


class Source(Protocol):
    """Read normalized items from an external source."""

    name: str

    def collect(self) -> list[Item]: ...


class HttpClient(Protocol):
    """Minimal outbound HTTP client."""

    def get(self, url: str, *, accept: str | None = None) -> bytes: ...

    def get_json(self, url: str) -> Any: ...


class StateStore(Protocol):
    """Persistent JSON state used for dedupe and snapshots."""

    def load(self, namespace: str) -> dict[str, Any]: ...

    def save(self, namespace: str, value: dict[str, Any]) -> None: ...


class Clock(Protocol):
    """Injectable wall clock."""

    def now(self) -> datetime: ...

    def today(self) -> date: ...


class Notifier(Protocol):
    """Destination for verbatim alerts."""

    def send(self, channel: str, message: str) -> None: ...


class MarketData(Protocol):
    """Market quote interface used by alert policies."""

    def change(self, symbol: str) -> PriceChange | None: ...

    def fundamentals(self, symbol: str) -> dict[str, Any]: ...


class CommandRunner(Protocol):
    """Safe subprocess interface used by integrations."""

    def run(self, args: list[str], *, timeout: int = 120) -> tuple[int, str, str]: ...


class Discovery(Protocol):
    """Optional public-source discovery used by the setup interview."""

    def youtube_channel(self, handle: str) -> dict[str, str] | None: ...

    def app_store_app(self, name: str) -> dict[str, str] | None: ...

    def topic_sources(self, topic: str) -> dict[str, Any]: ...

    def github_repositories(self, topic: str) -> list[dict[str, Any]]: ...


class ConfigRepository(Protocol):
    """Read and atomically replace the non-secret YAML configuration set."""

    root: Path

    def read(self, name: str) -> dict[str, Any] | None: ...

    def read_template(self, name: str) -> dict[str, Any]: ...

    def write(self, files: dict[str, dict[str, Any]]) -> None: ...


class ChangeRepository(Protocol):
    """Persistence for pending and applied reviewable changes."""

    def save(self, change_id: str, value: dict[str, Any]) -> None: ...

    def load(self, change_id: str) -> dict[str, Any]: ...

    def list(self) -> list[dict[str, Any]]: ...
