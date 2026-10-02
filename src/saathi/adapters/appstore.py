"""Apple App Store public-review adapter."""

from __future__ import annotations

from saathi.domain.models import Item
from saathi.domain.ports import HttpClient


class AppStoreReviewsSource:
    """Collect recent US App Store reviews without authentication."""

    def __init__(self, name: str, app_id: str, http: HttpClient, limit: int = 6) -> None:
        self.name = name
        self._app_id = app_id
        self._http = http
        self._limit = limit

    def collect(self) -> list[Item]:
        """Normalize review entries."""

        url = (
            "https://itunes.apple.com/us/rss/customerreviews/"
            f"id={self._app_id}/sortby=mostrecent/json"
        )
        data = self._http.get_json(url)
        if not isinstance(data, dict):
            return []
        feed = data.get("feed")
        entries = feed.get("entry", []) if isinstance(feed, dict) else []
        items: list[Item] = []
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict) or "im:rating" not in entry:
                continue
            rating = entry["im:rating"].get("label", "?")
            title = entry.get("title", {}).get("label", "Review")
            body = entry.get("content", {}).get("label", "")
            review_id = entry.get("id", {}).get("label", "")
            items.append(
                Item(
                    title=f"{title} ({rating}/5)",
                    url=review_id,
                    source=self.name,
                    summary=str(body)[:280],
                )
            )
            if len(items) == self._limit:
                break
        return items
