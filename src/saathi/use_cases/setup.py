"""Catalog-driven guided setup use case."""

from __future__ import annotations

import copy
import difflib
from typing import Any

import yaml

from saathi.domain.catalog import Addon, Capability
from saathi.domain.config import ConfigError, require_mapping
from saathi.domain.ports import ConfigRepository, Discovery
from saathi.domain.wizard import InitPlan, https_host

CONFIG_NAMES = ("profile", "sources", "watchlist", "jobs", "discord", "limits", "stack")
_MARKET_CAPABILITIES = {"markets_brief", "markets_alerts", "fundamentals", "deep_dive"}
_SENSITIVE_KEYS = ("secret", "token", "password", "api_key", "credential", "private_key")


def build_init_plan(
    repository: ConfigRepository,
    capabilities: dict[str, Capability],
    addons: dict[str, Addon],
    answers: dict[str, Any],
    discovery: Discovery | None = None,
) -> InitPlan:
    """Turn validated interview answers into existing Saathi config shapes."""

    _reject_secret_answers(answers)
    selected = _string_list(answers.get("capabilities"), "capabilities")
    if not selected:
        raise ConfigError("choose at least one capability")
    unknown = sorted(set(selected) - capabilities.keys())
    if unknown:
        raise ConfigError(f"unknown capabilities: {', '.join(unknown)}")
    addon_ids = _string_list(answers.get("addons", []), "addons")
    unknown_addons = sorted(set(addon_ids) - addons.keys())
    if unknown_addons:
        raise ConfigError(f"unknown add-ons: {', '.join(unknown_addons)}")

    templates = {name: copy.deepcopy(repository.read_template(name)) for name in CONFIG_NAMES}
    responses = dict(answers)
    nested = answers.get("responses")
    if nested is not None:
        responses.update(require_mapping(nested, "responses"))
    profile_text = _required_answer(answers, "profile")
    timezone_name = str(answers.get("timezone", "UTC"))
    display_name = str(answers.get("display_name", "the owner"))
    topics = _answer_list(responses, "topics")
    languages = _answer_list(responses, "languages")
    platforms = _answer_list(responses, "content_platforms")
    templates["profile"] = {
        "owner": {
            "display_name": display_name,
            "timezone": timezone_name,
            "profile": profile_text,
            "roles": _answer_list(responses, "roles"),
            "interests": topics,
            "content": {
                "audiences": _answer_list(responses, "audiences"),
                "platforms": platforms,
                "languages": languages,
                "preferences": _content_preferences(responses),
            },
        },
        "capabilities": list(selected),
        "rules": list(templates["profile"].get("rules", [])),
    }

    all_collectors = require_mapping(templates["sources"].get("collectors"), "collectors")
    collector_names = {
        collector
        for capability_id in selected
        for collector in capabilities[capability_id].collectors
    }
    templates["sources"]["collectors"] = {
        name: value for name, value in all_collectors.items() if name in collector_names
    }
    _customize_sources(templates["sources"], responses)

    schedules_raw = answers.get("schedules", {})
    schedules = require_mapping(schedules_raw, "schedules")
    jobs: list[dict[str, Any]] = []
    seen_jobs: set[str] = set()
    tickers = _tickers(responses)
    for capability_id in selected:
        capability = capabilities[capability_id]
        for raw in capability.jobs:
            job = copy.deepcopy(raw)
            name = str(job["name"])
            if name in seen_jobs:
                continue
            seen_jobs.add(name)
            override = schedules.get(
                capability_id, schedules.get(name, capability.default_schedule)
            )
            if not isinstance(override, str) or not override:
                raise ConfigError(f"schedule for {capability_id} must be a non-empty string")
            job["schedule"] = override
            command = job.get("command")
            if isinstance(command, list) and capability_id in {"fundamentals", "deep_dive"}:
                selected_tickers = tickers if capability_id == "fundamentals" else tickers[:1]
                if not selected_tickers:
                    raise ConfigError(f"{capability_id} requires at least one ticker")
                job["command"] = [*command, *selected_tickers]
            jobs.append(job)
    templates["jobs"] = {"jobs": jobs}

    channels = ["direct-message"]
    for capability_id in selected:
        channels.extend(capabilities[capability_id].channels)
    templates["discord"] = {
        "guild_name": str(answers.get("guild_name", "My private agent")),
        "channels": _unique(value for value in channels if value != "direct-message"),
        "direct_message_alias": "direct-message",
    }
    templates["watchlist"]["tickers"] = tickers
    templates["stack"] = _stack_for(templates["stack"], answers)

    notes: list[str] = []
    if bool(answers.get("discover", False)):
        if discovery is None:
            raise ConfigError("discovery was requested but no discovery adapter is configured")
        notes.extend(_discover(templates["sources"], responses, discovery))
    _validate_source_urls(templates["sources"])
    selected_addons = tuple(_unique(addon_ids))
    suggested = _unique(
        addon for capability_id in selected for addon in capabilities[capability_id].addons
    )
    if suggested:
        notes.append("Optional add-ons available (never auto-installed): " + ", ".join(suggested))
    return InitPlan(templates, tuple(selected), selected_addons, tuple(notes))


def render_init_plan(plan: InitPlan, repository: ConfigRepository, addons: dict[str, Addon]) -> str:
    """Render a human-readable config/job/channel/add-on plan and unified diff."""

    lines = ["PLAN", "Capabilities: " + ", ".join(plan.selected_capabilities)]
    jobs = plan.files["jobs"].get("jobs", [])
    channels = plan.files["discord"].get("channels", [])
    job_names = (str(row.get("name")) for row in jobs if isinstance(row, dict))
    lines.append("Jobs: " + ", ".join(job_names))
    lines.append("Channels: " + ", ".join(str(value) for value in channels))
    for note in plan.notes:
        lines.append(f"Note: {note}")
    for name in CONFIG_NAMES:
        before = repository.read(name) or {}
        lines.extend(_mapping_diff(name, before, plan.files[name]))
    if plan.selected_addons:
        lines.append("Add-ons (commands are printed only; Saathi will not run them):")
        for addon_id in plan.selected_addons:
            addon = addons[addon_id]
            lines.append(f"  {addon.name}: {addon.url}")
            lines.append(f"    Licence: {addon.licence}; RAM: {addon.ram}; risks: {addon.risks}")
            lines.extend(f"    $ {step}" for step in addon.install_steps)
    return "\n".join(lines)


def apply_init_plan(plan: InitPlan, repository: ConfigRepository) -> None:
    """Persist an approved plan using the repository's atomic writer."""

    repository.write(plan.files)


def _mapping_diff(name: str, before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    old = yaml.safe_dump(before, sort_keys=False).splitlines()
    new = yaml.safe_dump(after, sort_keys=False).splitlines()
    return list(
        difflib.unified_diff(old, new, fromfile=f"config/{name}.yaml", tofile=f"config/{name}.yaml")
    )


def _customize_sources(sources: dict[str, Any], answers: dict[str, Any]) -> None:
    collectors = require_mapping(sources.get("collectors"), "collectors")
    github = collectors.get("github_trending")
    if isinstance(github, dict):
        rows = github.get("sources")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            values = _answer_list(answers, "github_topics")
            if values:
                rows[0]["topics"] = values
    industry = collectors.get("industry_signals")
    if isinstance(industry, dict):
        terms = [str(answers.get("company", "")), *_answer_list(answers, "competitors")]
        terms = [term for term in terms if term]
        rows = industry.get("sources")
        if terms and isinstance(rows, list) and rows and isinstance(rows[0], dict):
            rows[0]["query"] = " OR ".join(terms)
    policy = collectors.get("policy_watch")
    if isinstance(policy, dict):
        terms = _answer_list(answers, "policy_topics")
        if terms:
            for row in policy.get("sources", []):
                if isinstance(row, dict):
                    key = "term" if row.get("type") == "federal_register" else "query"
                    row[key] = " OR ".join(terms)
    rotation = collectors.get("research_rotation")
    engineering = _answer_list(answers, "engineering_topics")
    if isinstance(rotation, dict) and engineering:
        days = require_mapping(rotation.get("days"), "research_rotation.days")
        for index, title in enumerate(engineering[: len(days)]):
            day = days.get(str(index))
            if isinstance(day, dict):
                day["title"] = title


def _discover(sources: dict[str, Any], answers: dict[str, Any], discovery: Discovery) -> list[str]:
    collectors = require_mapping(sources.get("collectors"), "collectors")
    notes: list[str] = []
    creator = collectors.get("creator_radar")
    if isinstance(creator, dict):
        rows = creator.setdefault("sources", [])
        if isinstance(rows, list):
            for handle in _answer_list(answers, "creators"):
                found = discovery.youtube_channel(handle)
                if found:
                    http = require_mapping(sources.get("http"), "http")
                    hosts = http.setdefault("allowed_hosts", [])
                    if isinstance(hosts, list):
                        hosts.append("www.youtube.com")
                    rows.append(
                        {
                            "name": found["handle"],
                            "type": "youtube",
                            "channel_id": found["channel_id"],
                        }
                    )
    industry = collectors.get("industry_signals")
    if isinstance(industry, dict):
        rows = industry.setdefault("sources", [])
        if isinstance(rows, list):
            for app in _answer_list(answers, "apps"):
                found = discovery.app_store_app(app)
                if found:
                    http = require_mapping(sources.get("http"), "http")
                    hosts = http.setdefault("allowed_hosts", [])
                    if isinstance(hosts, list):
                        hosts.append("itunes.apple.com")
                    rows.append(
                        {"name": found["name"], "type": "appstore", "app_id": found["app_id"]}
                    )
    news = collectors.get("ai_news")
    if isinstance(news, dict):
        rows = news.setdefault("sources", [])
        http = require_mapping(sources.get("http"), "http")
        hosts = http.setdefault("allowed_hosts", [])
        if isinstance(rows, list) and isinstance(hosts, list):
            for topic in _answer_list(answers, "topics"):
                suggestions = discovery.topic_sources(topic)
                feeds = suggestions.get("feeds", [])
                if isinstance(feeds, list):
                    for feed in feeds:
                        if isinstance(feed, dict) and isinstance(feed.get("url"), str):
                            rows.append(
                                {
                                    "name": str(feed.get("name", topic)),
                                    "type": "rss",
                                    "url": feed["url"],
                                }
                            )
                            hosts.append(https_host(feed["url"]))
    for topic in _answer_list(answers, "github_search"):
        for repo in discovery.github_repositories(topic):
            notes.append(
                "GitHub suggestion (not installed): "
                f"{repo['name']} — {repo['stars']} stars, {repo['licence']}, "
                f"last push {repo['last_push']}"
            )
    return notes


def _stack_for(template: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(template)
    privacy = str(answers.get("privacy", "balanced")).lower()
    if privacy in {"maximum", "local", "maximum privacy"}:
        value["model"] = {"provider": "ollama", "base_url": "http://127.0.0.1:11434/v1"}
    elif privacy not in {"balanced", "cloud"}:
        raise ConfigError("privacy must be balanced/cloud or maximum/local")
    chat_app = str(answers.get("chat_app", "discord")).lower()
    notifier = require_mapping(value.get("notifier"), "notifier")
    notifier["backend"] = chat_app
    notifier["target_prefix"] = chat_app
    return value


def _validate_source_urls(sources: dict[str, Any]) -> None:
    http = require_mapping(sources.get("http"), "http")
    hosts = http.get("allowed_hosts")
    if not isinstance(hosts, list):
        raise ConfigError("http.allowed_hosts must be a list")
    http["allowed_hosts"] = sorted(_unique(str(value).lower() for value in hosts))
    collectors = require_mapping(sources.get("collectors"), "collectors")
    for collector in collectors.values():
        if not isinstance(collector, dict):
            continue
        for row in collector.get("sources", []):
            if not isinstance(row, dict) or not isinstance(row.get("url"), str):
                continue
            host = https_host(row["url"])
            if host not in http["allowed_hosts"]:
                raise ConfigError(f"source host is not allowlisted: {host}")


def _content_preferences(answers: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for key in ("linkedin_style", "reel_length", "youtube_language"):
        value = answers.get(key)
        if isinstance(value, str) and value:
            result.append(f"{key.replace('_', ' ')}: {value}")
    return result


def _tickers(answers: dict[str, Any]) -> list[str]:
    values = _answer_list(answers, "tickers")
    return [value.upper() for value in values]


def _required_answer(answers: dict[str, Any], key: str) -> str:
    value = answers.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"answers.{key} must be a non-empty string")
    return value.strip()


def _answer_list(answers: dict[str, Any], key: str) -> list[str]:
    value = answers.get(key, [])
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return _string_list(value, key)


def _string_list(value: object, context: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ConfigError(f"{context} must be a list of non-empty strings")
    return [str(item) for item in value]


def _unique(values: Any) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _reject_secret_answers(value: object, path: str = "answers") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(word in normalized for word in _SENSITIVE_KEYS):
                raise ConfigError(
                    "answers files must not contain secrets; use hidden input and "
                    "~/.hermes/.env mode 600"
                )
            _reject_secret_answers(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_answers(child, f"{path}[{index}]")
