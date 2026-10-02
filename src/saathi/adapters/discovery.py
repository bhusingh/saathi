"""Allowlisted, read-only discovery adapters for the setup wizard."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from saathi.domain.config import load_yaml, require_mapping
from saathi.domain.ports import HttpClient

_CHANNEL_ID = re.compile(rb'"(?:externalId|channelId)"\s*:\s*"(UC[A-Za-z0-9_-]{20,})"')


class CatalogDiscovery:
    """Discover public identifiers and curated sources without installing tools."""

    def __init__(self, http: HttpClient, curated_path: Path) -> None:
        self._http = http
        self._curated = load_yaml(curated_path)

    def youtube_channel(self, handle: str) -> dict[str, str] | None:
        """Resolve a public handle from YouTube page metadata."""

        normalized = handle.strip().lstrip("@")
        if not normalized:
            return None
        body = self._http.get(f"https://www.youtube.com/@{normalized}")
        match = _CHANNEL_ID.search(body)
        if match is None:
            return None
        return {"handle": f"@{normalized}", "channel_id": match.group(1).decode("ascii")}

    def app_store_app(self, name: str) -> dict[str, str] | None:
        """Resolve the first matching public iTunes Search result."""

        data = self._http.get_json(
            f"https://itunes.apple.com/search?term={quote_plus(name)}&entity=software&limit=1"
        )
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            return None
        results = data["results"]
        if not results or not isinstance(results[0], dict):
            return None
        row = results[0]
        track_id = row.get("trackId")
        track_name = row.get("trackName")
        if not isinstance(track_id, int) or not isinstance(track_name, str):
            return None
        return {"name": track_name, "app_id": str(track_id)}

    def topic_sources(self, topic: str) -> dict[str, Any]:
        """Return locally curated feeds and subreddits for a topic."""

        topics = require_mapping(self._curated.get("topics"), "topics")
        value = topics.get(topic.strip().lower(), {})
        return require_mapping(value, f"topics.{topic}")

    def github_repositories(self, topic: str) -> list[dict[str, Any]]:
        """Return safe repository facts; this adapter never clones or installs."""

        query = quote_plus(topic)
        data = self._http.get_json(
            f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=5"
        )
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return []
        result: list[dict[str, Any]] = []
        for value in data["items"]:
            if not isinstance(value, dict):
                continue
            licence = value.get("license")
            result.append(
                {
                    "name": str(value.get("full_name", "")),
                    "url": str(value.get("html_url", "")),
                    "stars": int(value.get("stargazers_count", 0)),
                    "licence": (
                        str(licence.get("spdx_id", "unknown"))
                        if isinstance(licence, dict)
                        else "unknown"
                    ),
                    "last_push": str(value.get("pushed_at", "")),
                }
            )
        return result
