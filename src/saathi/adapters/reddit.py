"""Reddit public RSS adapter."""

from __future__ import annotations

from urllib.parse import quote

from saathi.adapters.rss import RssSource
from saathi.domain.ports import Clock, HttpClient


def reddit_source(
    subreddit: str,
    http: HttpClient,
    clock: Clock,
    *,
    query: str | None = None,
    limit: int = 8,
) -> RssSource:
    """Build a no-login Reddit RSS source without cookies."""

    if query:
        url = (
            f"https://www.reddit.com/r/{subreddit}/search.rss?q={quote(query)}"
            "&restrict_sr=1&sort=new&t=week"
        )
    else:
        url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=week"
    return RssSource(f"r/{subreddit}", url, http, clock, max_age_hours=24 * 8, limit=limit)
