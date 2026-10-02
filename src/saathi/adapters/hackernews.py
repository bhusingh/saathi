"""Hacker News API source."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from saathi.domain.models import Item
from saathi.domain.ports import HttpClient


class HackerNewsSource:
    """Select popular stories matching configured keywords."""

    name = "Hacker News"

    def __init__(
        self, http: HttpClient, keywords: list[str], *, minimum_score: int = 80, limit: int = 10
    ) -> None:
        self._http = http
        self._keywords = [keyword.lower() for keyword in keywords]
        self._minimum_score = minimum_score
        self._limit = limit

    def collect(self) -> list[Item]:
        """Fetch top-story details until enough configured matches are found."""

        story_ids = self._http.get_json("https://hacker-news.firebaseio.com/v0/topstories.json")
        if not isinstance(story_ids, list):
            return []
        items: list[Item] = []
        for story_id in story_ids[:120]:
            raw = self._http.get_json(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json")
            if not isinstance(raw, dict):
                continue
            story: dict[str, Any] = raw
            title = str(story.get("title", ""))
            score = int(story.get("score", 0))
            if score < self._minimum_score or not any(k in title.lower() for k in self._keywords):
                continue
            item_url = str(story.get("url") or f"https://news.ycombinator.com/item?id={story_id}")
            timestamp = story.get("time")
            published = (
                datetime.fromtimestamp(timestamp, tz=UTC) if isinstance(timestamp, int) else None
            )
            items.append(
                Item(
                    title=title,
                    url=item_url,
                    source=self.name,
                    published_at=published,
                    summary=f"{score} points, {int(story.get('descendants', 0))} comments",
                )
            )
            if len(items) == self._limit:
                break
        return items
