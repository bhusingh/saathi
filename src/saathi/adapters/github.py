"""GitHub repository search and snapshot deltas."""

from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any, cast
from urllib.parse import quote_plus

from saathi.domain.models import Item
from saathi.domain.ports import Clock, HttpClient, StateStore


def star_delta(history: dict[str, int], today: str, stars: int) -> tuple[int | None, int | None]:
    """Compute a delta from the latest prior snapshot."""

    previous_day = max((day for day in history if day < today), default=None)
    if previous_day is None:
        return None, None
    days = (date.fromisoformat(today) - date.fromisoformat(previous_day)).days
    return stars - history[previous_day], days


class GitHubTrendingSource:
    """Search configured topics and rank repositories by observed star gain."""

    name = "GitHub"

    def __init__(
        self,
        http: HttpClient,
        state: StateStore,
        clock: Clock,
        topics: list[str],
        *,
        limit: int = 25,
        rate_delay: float = 6.1,
    ) -> None:
        self._http = http
        self._state = state
        self._clock = clock
        self._topics = topics
        self._limit = limit
        self._rate_delay = rate_delay

    def collect(self) -> list[Item]:
        """Collect deduplicated topic results and update snapshots."""

        repositories: dict[str, dict[str, Any]] = {}
        since = (self._clock.today() - timedelta(days=60)).isoformat()
        for index, topic in enumerate(self._topics):
            query = quote_plus(f"topic:{topic} created:>{since}")
            data = self._http.get_json(
                f"https://api.github.com/search/repositories?q={query}"
                "&sort=stars&order=desc&per_page=15"
            )
            if isinstance(data, dict) and isinstance(data.get("items"), list):
                for raw in data["items"]:
                    if isinstance(raw, dict) and isinstance(raw.get("full_name"), str):
                        repositories[raw["full_name"]] = cast(dict[str, Any], raw)
            if index + 1 < len(self._topics) and self._rate_delay:
                time.sleep(self._rate_delay)
        return self._rank(repositories)

    def _rank(self, repositories: dict[str, dict[str, Any]]) -> list[Item]:
        snapshots = self._state.load("github_snapshots")
        today_date = self._clock.today()
        today = today_date.isoformat()
        cutoff = today_date - timedelta(days=30)
        snapshots = {
            name: history
            for name, history in snapshots.items()
            if _snapshot_is_recent(history, cutoff)
        }
        ranked: list[tuple[int, int, Item]] = []
        for name, repo in repositories.items():
            raw_history = snapshots.get(name, {})
            if not isinstance(raw_history, dict):
                raw_history = {}
            history = {
                str(day): int(value)
                for day, value in raw_history.items()
                if _is_iso_date(day) and isinstance(value, int)
            }
            stars = int(repo.get("stargazers_count", 0))
            gain, days = star_delta(history, today, stars)
            history[today] = stars
            snapshots[name] = dict(sorted(history.items())[-30:])
            change = f"+{gain} stars in {days}d" if gain is not None else "new to tracking"
            license_data = repo.get("license")
            license_name = (
                str(license_data.get("spdx_id", "n/a")) if isinstance(license_data, dict) else "n/a"
            )
            summary = (
                f"{stars} stars ({change}); language {repo.get('language') or 'n/a'}; "
                f"license {license_name}. {repo.get('description') or ''}"
            )
            item = Item(
                title=name,
                url=str(repo.get("html_url", "")),
                source=self.name,
                summary=summary,
                metadata={"stars": stars, "gain": gain},
            )
            ranked.append((gain if gain is not None else -1, stars, item))
        self._state.save("github_snapshots", snapshots)
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [item for _, _, item in ranked[: self._limit]]


def _is_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _last_snapshot_date(value: object) -> date | None:
    if not isinstance(value, dict):
        return None
    dates = [date.fromisoformat(day) for day in value if _is_iso_date(day)]
    return max(dates, default=None)


def _snapshot_is_recent(value: object, cutoff: date) -> bool:
    last_seen = _last_snapshot_date(value)
    return last_seen is not None and last_seen >= cutoff
