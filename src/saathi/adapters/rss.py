"""RSS and Atom source adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import struct_time
from typing import Any

import feedparser  # type: ignore[import-untyped]

from saathi.domain.formatting import clean_text
from saathi.domain.models import Item
from saathi.domain.ports import Clock, HttpClient


class RssSource:
    """Normalize an RSS/Atom feed into domain items."""

    def __init__(
        self,
        name: str,
        url: str,
        http: HttpClient,
        clock: Clock,
        *,
        max_age_hours: int = 48,
        limit: int = 15,
    ) -> None:
        self.name = name
        self._url = url
        self._http = http
        self._clock = clock
        self._max_age = timedelta(hours=max_age_hours)
        self._limit = limit

    @staticmethod
    def _instant(value: struct_time | None) -> datetime | None:
        if value is None:
            return None
        return datetime(*value[:6], tzinfo=UTC)

    def collect(self) -> list[Item]:
        """Fetch and normalize recent entries."""

        parsed = feedparser.parse(self._http.get(self._url))
        now = self._clock.now()
        items: list[Item] = []
        for raw in parsed.entries[:60]:
            entry: dict[str, Any] = dict(raw)
            published = self._instant(entry.get("published_parsed") or entry.get("updated_parsed"))
            if published is not None and now - published > self._max_age:
                continue
            url = str(entry.get("link", ""))
            title = clean_text(str(entry.get("title", "")), 180)
            if not url or not title:
                continue
            items.append(
                Item(
                    title=title,
                    url=url,
                    source=self.name,
                    published_at=published,
                    summary=clean_text(str(entry.get("summary", ""))),
                    metadata=entry,
                )
            )
            if len(items) == self._limit:
                break
        return items
