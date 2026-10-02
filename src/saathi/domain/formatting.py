"""Pure, deterministic data-sheet formatting."""

from __future__ import annotations

import re
from datetime import UTC
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from saathi.domain.models import Item, Sheet


def clean_text(value: str, limit: int = 280) -> str:
    """Remove markup and collapse whitespace in untrusted feed text."""

    text = re.sub(r"<[^>]+>", " ", unescape(value))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def canonical_url(url: str) -> str:
    """Normalize a URL and discard tracking parameters/fragments."""

    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.startswith("utm_")]
    normalized = (
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        urlencode(query),
        "",
    )
    return urlunsplit(normalized)


def format_item(item: Item, timezone_name: str = "UTC") -> str:
    """Format a source item with a citation-ready link."""

    when = "date n/a"
    if item.published_at is not None:
        instant = item.published_at
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        when = instant.astimezone(ZoneInfo(timezone_name)).strftime("%b %d %H:%M %Z")
    line = f"- [{item.source}] {clean_text(item.title, 180)} ({when}) <{item.url}>"
    summary_limit = item.metadata.get("summary_limit", 280)
    limit = summary_limit if isinstance(summary_limit, int) else 280
    return f"{line}\n  {clean_text(item.summary, limit)}" if item.summary else line


def format_sheet(sheet: Sheet, timezone_name: str = "UTC") -> str:
    """Render a complete collector sheet for stdout."""

    local = sheet.generated_at.astimezone(ZoneInfo(timezone_name))
    lines = [f"DATA SHEET: {sheet.title} - collected {local:%a %b %d %H:%M %Z}"]
    lines.extend(sheet.notes)
    for heading, items in sheet.sections:
        lines.extend(("", f"## {heading}"))
        lines.extend(format_item(item, timezone_name) for item in items)
    if sheet.errors:
        lines.append("")
        lines.extend(
            f"(source unavailable: {error.source} - {error.reason})" for error in sheet.errors
        )
    return "\n".join(lines).rstrip()
