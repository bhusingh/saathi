"""Propose, approve, audit, and undo catalog-aware configuration changes."""

from __future__ import annotations

import copy
import difflib
import hashlib
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import yaml

from saathi.domain.catalog import Capability
from saathi.domain.config import ConfigError, require_mapping
from saathi.domain.ports import ChangeRepository, ConfigRepository
from saathi.domain.wizard import https_host, validate_change_request

_URL = re.compile(r"https://[^\s<>'\"]+")
_SYMBOL = re.compile(r"\b[A-Z][A-Z0-9.-]{0,9}\b")
_SENSITIVE_KEYS = ("secret", "token", "password", "api_key", "credential", "private_key")


def propose_change(
    request: str,
    repository: ConfigRepository,
    changes: ChangeRepository,
    capabilities: dict[str, Capability],
    now: datetime,
) -> tuple[str, str]:
    """Map a narrow owner request to a staged deterministic change."""

    validate_change_request(request)
    normalized = request.strip().lower()
    before, after = _plan_change(request, normalized, repository, capabilities)
    _reject_secret_fields(before)
    _reject_secret_fields(after)
    diff = _files_diff(before, after)
    if not diff:
        raise ConfigError("request would not change the current configuration")
    stamp = now.isoformat()
    digest = hashlib.sha256(f"{stamp}\0{request}".encode()).hexdigest()[:8]
    change_id = f"chg-{now.strftime('%Y%m%d%H%M%S')}-{digest}"
    changes.save(
        change_id,
        {
            "id": change_id,
            "status": "pending",
            "request": request,
            "created_at": stamp,
            "before": before,
            "after": after,
            "diff": diff,
            "undo_command": "saathi config undo",
        },
    )
    return change_id, diff


def apply_change(
    change_id: str,
    repository: ConfigRepository,
    changes: ChangeRepository,
    now: datetime,
) -> str:
    """Apply an explicitly approved proposal if it is still current."""

    record = changes.load(change_id)
    if record.get("status") != "pending":
        raise ConfigError(f"change {change_id} is not pending")
    before = _file_set(record.get("before"), "before")
    after = _file_set(record.get("after"), "after")
    _assert_current(repository, before)
    repository.write(after)
    record["status"] = "applied"
    record["applied_at"] = now.isoformat()
    changes.save(change_id, record)
    return str(record.get("diff", ""))


def undo_latest(
    repository: ConfigRepository, changes: ChangeRepository, now: datetime
) -> tuple[str, str]:
    """Undo the most recently applied, not-yet-undone change."""

    applied = [record for record in changes.list() if record.get("status") == "applied"]
    if not applied:
        raise ConfigError("there is no applied configuration change to undo")
    record = max(applied, key=lambda value: str(value.get("applied_at", "")))
    change_id = str(record.get("id", ""))
    before = _file_set(record.get("before"), "before")
    after = _file_set(record.get("after"), "after")
    _assert_current(repository, after)
    repository.write(before)
    undo_diff = _files_diff(after, before)
    record["status"] = "undone"
    record["undone_at"] = now.isoformat()
    record["undo_diff"] = undo_diff
    changes.save(change_id, record)
    return change_id, undo_diff


def _plan_change(
    request: str,
    normalized: str,
    repository: ConfigRepository,
    capabilities: dict[str, Capability],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    url_match = _URL.search(request)
    if url_match:
        return _source_url_change(url_match.group(0).rstrip(".,)"), normalized, repository)
    if "reddit" in normalized and any(word in normalized for word in ("stop", "remove", "disable")):
        return _stop_reddit(repository)
    if "shorter" in normalized and "linkedin" in normalized:
        return _shorter_linkedin(repository)
    capability = _mentioned_capability(normalized, capabilities)
    if capability and re.search(r"\b(enable|add|start)\b", normalized):
        return _enable_capability(repository, capability)
    if capability and re.search(r"\b(disable|remove|stop)\b", normalized):
        return _disable_capability(repository, capability)
    if capability and ("daily" in normalized or "weekly" in normalized):
        return _change_schedule(repository, capability, "daily" in normalized)
    track = re.search(r"\btrack\s+(.+?)\s+news(?:\s+daily)?$", normalized)
    if track:
        return _track_news(repository, track.group(1), daily="daily" in normalized)
    symbols = _SYMBOL.findall(request)
    if symbols and re.search(r"\b(add|track|watch)\b", normalized):
        return _ticker_change(repository, symbols, remove=False)
    if symbols and re.search(r"\b(remove|stop|unwatch)\b", normalized):
        return _ticker_change(repository, symbols, remove=True)
    raise ConfigError(
        "request is not a supported deterministic config change; try enable/disable CAPABILITY, "
        "add/remove TICKER, stop Reddit, add an HTTPS feed, or change a capability daily/weekly"
    )


def _ticker_change(
    repository: ConfigRepository, symbols: list[str], *, remove: bool
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    current = _required_config(repository, "watchlist")
    updated = copy.deepcopy(current)
    values = updated.get("tickers")
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ConfigError("watchlist.tickers must be a list of strings")
    if remove:
        updated["tickers"] = [value for value in values if value.upper() not in symbols]
    else:
        updated["tickers"] = list(dict.fromkeys([*values, *symbols]))
    return {"watchlist": current}, {"watchlist": updated}


def _stop_reddit(
    repository: ConfigRepository,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    current = _required_config(repository, "sources")
    updated = copy.deepcopy(current)
    collectors = require_mapping(updated.get("collectors"), "collectors")
    for collector in collectors.values():
        if isinstance(collector, dict) and isinstance(collector.get("sources"), list):
            collector["sources"] = [
                row
                for row in collector["sources"]
                if not isinstance(row, dict) or row.get("type") != "reddit"
            ]
    return {"sources": current}, {"sources": updated}


def _shorter_linkedin(
    repository: ConfigRepository,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    current = _required_config(repository, "profile")
    updated = copy.deepcopy(current)
    owner = require_mapping(updated.get("owner"), "owner")
    content = owner.setdefault("content", {})
    content = require_mapping(content, "owner.content")
    preferences = content.setdefault("preferences", [])
    valid_preferences = isinstance(preferences, list) and all(
        isinstance(value, str) for value in preferences
    )
    if not valid_preferences:
        raise ConfigError("owner.content.preferences must be a list of strings")
    preference = "LinkedIn drafts: keep drafts under 900 characters."
    if preference not in preferences:
        preferences.append(preference)
    return {"profile": current}, {"profile": updated}


def _source_url_change(
    url: str, normalized: str, repository: ConfigRepository
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    host = https_host(url)
    current = _required_config(repository, "sources")
    updated = copy.deepcopy(current)
    collectors = require_mapping(updated.get("collectors"), "collectors")
    news = require_mapping(collectors.get("ai_news"), "collectors.ai_news")
    rows = news.get("sources")
    if not isinstance(rows, list):
        raise ConfigError("collectors.ai_news.sources must be a list")
    removing = bool(re.search(r"\b(remove|stop|delete)\b", normalized))
    if removing:
        news["sources"] = [
            row for row in rows if not isinstance(row, dict) or row.get("url") != url
        ]
    else:
        if not any(isinstance(row, dict) and row.get("url") == url for row in rows):
            rows.append({"name": urlsplit(url).hostname or "Added feed", "type": "rss", "url": url})
        http = require_mapping(updated.get("http"), "http")
        hosts = http.get("allowed_hosts")
        if not isinstance(hosts, list) or not all(isinstance(value, str) for value in hosts):
            raise ConfigError("http.allowed_hosts must be a list of strings")
        http["allowed_hosts"] = sorted(set([*hosts, host]))
    return {"sources": current}, {"sources": updated}


def _track_news(
    repository: ConfigRepository, topic: str, *, daily: bool
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    sources = _required_config(repository, "sources")
    jobs = _required_config(repository, "jobs")
    next_sources = copy.deepcopy(sources)
    next_jobs = copy.deepcopy(jobs)
    collectors = require_mapping(next_sources.get("collectors"), "collectors")
    news = require_mapping(collectors.get("ai_news"), "collectors.ai_news")
    rows = news.get("sources")
    if not isinstance(rows, list):
        raise ConfigError("collectors.ai_news.sources must be a list")
    google = next(
        (row for row in rows if isinstance(row, dict) and row.get("type") == "google_news"),
        None,
    )
    if not isinstance(google, dict):
        rows.append({"name": f"{topic.title()} news", "type": "google_news", "query": topic})
    elif topic not in str(google.get("query", "")).lower():
        google["query"] = f"{google.get('query', '')} OR {topic}".strip()
    if daily:
        for job in next_jobs.get("jobs", []):
            if isinstance(job, dict) and job.get("name") == "ai news":
                job["schedule"] = "30 6 * * *"
    return {"sources": sources, "jobs": jobs}, {"sources": next_sources, "jobs": next_jobs}


def _enable_capability(
    repository: ConfigRepository, capability: Capability
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    names = ("profile", "sources", "jobs", "discord")
    before = {name: _required_config(repository, name) for name in names}
    after = copy.deepcopy(before)
    profile_caps = after["profile"].setdefault("capabilities", [])
    if not isinstance(profile_caps, list):
        raise ConfigError("profile.capabilities must be a list")
    if capability.id not in profile_caps:
        profile_caps.append(capability.id)
    collectors = require_mapping(after["sources"].get("collectors"), "collectors")
    template_collectors = require_mapping(
        repository.read_template("sources").get("collectors"), "collectors"
    )
    for name in capability.collectors:
        if name not in collectors:
            collectors[name] = copy.deepcopy(template_collectors[name])
    jobs = after["jobs"].get("jobs")
    if not isinstance(jobs, list):
        raise ConfigError("jobs must be a list")
    existing = {str(row.get("name")) for row in jobs if isinstance(row, dict)}
    for raw in capability.jobs:
        if str(raw["name"]) not in existing:
            row = copy.deepcopy(raw)
            row["schedule"] = capability.default_schedule
            command = row.get("command")
            if isinstance(command, list) and capability.id in {"fundamentals", "deep_dive"}:
                watchlist = _required_config(repository, "watchlist").get("tickers", [])
                if not isinstance(watchlist, list) or not watchlist:
                    raise ConfigError(f"{capability.id} requires at least one ticker")
                arguments = watchlist if capability.id == "fundamentals" else watchlist[:1]
                row["command"] = [*command, *arguments]
            jobs.append(row)
    channels = after["discord"].get("channels")
    if not isinstance(channels, list):
        raise ConfigError("discord.channels must be a list")
    after["discord"]["channels"] = list(dict.fromkeys([*channels, *capability.channels]))
    return before, after


def _disable_capability(
    repository: ConfigRepository, capability: Capability
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    names = ("profile", "sources", "jobs", "discord")
    before = {name: _required_config(repository, name) for name in names}
    after = copy.deepcopy(before)
    profile_caps = after["profile"].get("capabilities", [])
    if isinstance(profile_caps, list):
        after["profile"]["capabilities"] = [
            value for value in profile_caps if value != capability.id
        ]
    removed_jobs = {str(row["name"]) for row in capability.jobs}
    jobs = after["jobs"].get("jobs")
    if not isinstance(jobs, list):
        raise ConfigError("jobs must be a list")
    after["jobs"]["jobs"] = [
        row for row in jobs if not isinstance(row, dict) or str(row.get("name")) not in removed_jobs
    ]
    remaining_jobs = after["jobs"]["jobs"]
    collectors_in_use = {
        str(row.get("collector"))
        for row in remaining_jobs
        if isinstance(row, dict) and isinstance(row.get("collector"), str)
    }
    collectors = require_mapping(after["sources"].get("collectors"), "collectors")
    for name in capability.collectors:
        if name not in collectors_in_use:
            collectors.pop(name, None)
    channels_in_use = {str(row.get("channel")) for row in remaining_jobs if isinstance(row, dict)}
    channels = after["discord"].get("channels")
    if isinstance(channels, list):
        after["discord"]["channels"] = [value for value in channels if value in channels_in_use]
    return before, after


def _change_schedule(
    repository: ConfigRepository, capability: Capability, daily: bool
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    current = _required_config(repository, "jobs")
    updated = copy.deepcopy(current)
    names = {str(row["name"]) for row in capability.jobs}
    schedule = "30 6 * * *" if daily else "0 9 * * 1"
    for row in updated.get("jobs", []):
        if isinstance(row, dict) and str(row.get("name")) in names:
            row["schedule"] = schedule
    return {"jobs": current}, {"jobs": updated}


def _mentioned_capability(
    normalized: str, capabilities: dict[str, Capability]
) -> Capability | None:
    for capability in capabilities.values():
        aliases = {
            capability.id.lower(),
            capability.id.replace("_", " ").lower(),
            capability.title.lower(),
        }
        if any(alias in normalized for alias in aliases):
            return capability
    return None


def _required_config(repository: ConfigRepository, name: str) -> dict[str, Any]:
    value = repository.read(name)
    if value is None:
        raise ConfigError(f"config/{name}.yaml does not exist; run saathi init first")
    return value


def _assert_current(repository: ConfigRepository, expected: dict[str, dict[str, Any]]) -> None:
    for name, value in expected.items():
        if repository.read(name) != value:
            raise ConfigError(f"config/{name}.yaml changed since this proposal; propose it again")


def _file_set(value: object, context: str) -> dict[str, dict[str, Any]]:
    rows = require_mapping(value, context)
    return {name: require_mapping(row, f"{context}.{name}") for name, row in rows.items()}


def _files_diff(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    for name in sorted(set(before) | set(after)):
        old = yaml.safe_dump(before.get(name, {}), sort_keys=False).splitlines()
        new = yaml.safe_dump(after.get(name, {}), sort_keys=False).splitlines()
        lines.extend(
            difflib.unified_diff(
                old,
                new,
                fromfile=f"config/{name}.yaml",
                tofile=f"config/{name}.yaml",
                lineterm="",
            )
        )
    return "\n".join(lines)


def _reject_secret_fields(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(word in normalized for word in _SENSITIVE_KEYS):
                raise ConfigError(
                    "configuration files must not contain secrets; move them to "
                    "~/.hermes/.env with mode 600"
                )
            _reject_secret_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secret_fields(child)
