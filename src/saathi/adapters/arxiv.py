"""arXiv Atom search adapter."""

from __future__ import annotations

from urllib.parse import quote_plus

from saathi.adapters.rss import RssSource
from saathi.domain.ports import Clock, HttpClient


def arxiv_source(
    name: str, query: str, http: HttpClient, clock: Clock, limit: int = 25
) -> RssSource:
    """Build an arXiv API source sorted by submission time."""

    url = (
        "https://export.arxiv.org/api/query?search_query="
        f"{quote_plus(query)}&sortBy=submittedDate&sortOrder=descending&max_results={limit}"
    )
    return RssSource(name, url, http, clock, max_age_hours=24 * 14, limit=limit)
