"""Google News RSS adapter."""

from __future__ import annotations

from urllib.parse import quote_plus

from saathi.adapters.rss import RssSource
from saathi.domain.ports import Clock, HttpClient


def google_news_source(
    name: str, query: str, http: HttpClient, clock: Clock, limit: int = 8
) -> RssSource:
    """Build a time-bounded public Google News RSS source."""

    url = (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query)}+when:2d&hl=en-US&gl=US&ceid=US:en"
    )
    return RssSource(name, url, http, clock, max_age_hours=48, limit=limit)
