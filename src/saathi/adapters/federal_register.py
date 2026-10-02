"""Federal Register public API adapter."""

from __future__ import annotations

from datetime import timedelta
from urllib.parse import quote_plus

from saathi.domain.models import Item
from saathi.domain.ports import Clock, HttpClient


class FederalRegisterSource:
    """Search recent federal documents for a configured term."""

    def __init__(self, term: str, http: HttpClient, clock: Clock, lookback_days: int = 10) -> None:
        self.name = f"Federal Register: {term}"
        self._term = term
        self._http = http
        self._clock = clock
        self._lookback_days = lookback_days

    def collect(self) -> list[Item]:
        """Fetch and normalize recent documents."""

        since = (self._clock.today() - timedelta(days=self._lookback_days)).isoformat()
        url = (
            "https://www.federalregister.gov/api/v1/documents.json?per_page=8&order=newest"
            f"&conditions%5Bterm%5D={quote_plus(self._term)}"
            f"&conditions%5Bpublication_date%5D%5Bgte%5D={since}"
        )
        data = self._http.get_json(url)
        results = data.get("results", []) if isinstance(data, dict) else []
        return [
            Item(
                title=str(row.get("title", "Untitled document")),
                url=str(row.get("html_url", "")),
                source=self.name,
                summary=str(row.get("abstract") or "")[:280],
                metadata={"publication_date": row.get("publication_date")},
            )
            for row in results
            if isinstance(row, dict) and row.get("html_url")
        ]
