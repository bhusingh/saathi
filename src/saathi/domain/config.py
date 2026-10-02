"""Strict YAML configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from saathi.domain.models import JobSpec


class ConfigError(ValueError):
    """Raised when a configuration file has an invalid shape."""


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping with safe parsing and useful errors."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot load {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return cast(dict[str, Any], raw)


def require_mapping(value: object, context: str) -> dict[str, Any]:
    """Validate and narrow an arbitrary value to a string-key mapping."""

    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ConfigError(f"{context} must be a mapping")
    return cast(dict[str, Any], value)


def require_list(value: object, context: str) -> list[Any]:
    """Validate and narrow an arbitrary value to a list."""

    if not isinstance(value, list):
        raise ConfigError(f"{context} must be a list")
    return value


def required_string(row: dict[str, Any], key: str, context: str) -> str:
    """Return a required non-empty string field."""

    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context}.{key} must be a non-empty string")
    return value


def load_jobs(path: Path) -> list[JobSpec]:
    """Load validated scheduled-job definitions."""

    root = load_yaml(path)
    rows = require_list(root.get("jobs"), "jobs")
    jobs: list[JobSpec] = []
    names: set[str] = set()
    for index, value in enumerate(rows):
        context = f"jobs[{index}]"
        row = require_mapping(value, context)
        name = required_string(row, "name", context)
        if name in names:
            raise ConfigError(f"duplicate job name: {name}")
        names.add(name)
        prompt = row.get("prompt_file")
        if prompt is not None and not isinstance(prompt, str):
            raise ConfigError(f"{context}.prompt_file must be a string or null")
        agent = row.get("agent", True)
        if not isinstance(agent, bool):
            raise ConfigError(f"{context}.agent must be a boolean")
        collector_value = row.get("collector")
        command_value = row.get("command")
        if (collector_value is None) == (command_value is None):
            raise ConfigError(f"{context} must define exactly one of collector or command")
        collector = None
        command: tuple[str, ...] = ()
        if collector_value is not None:
            collector = required_string(row, "collector", context)
        else:
            values = _string_list(command_value, f"{context}.command")
            command = tuple(values)
        jobs.append(
            JobSpec(
                name=name,
                schedule=required_string(row, "schedule", context),
                collector=collector,
                prompt_file=prompt,
                channel=required_string(row, "channel", context),
                agent=agent,
                command=command,
            )
        )
    return jobs


@dataclass(frozen=True, slots=True)
class ConfigPaths:
    """Locations of operator-managed configuration files."""

    root: Path

    def named(self, name: str) -> Path:
        """Resolve a configured YAML file, falling back to its example."""

        configured = self.root / f"{name}.yaml"
        return configured if configured.exists() else self.root / f"{name}.example.yaml"


def validate_profile(value: dict[str, Any]) -> None:
    """Validate the profile fields consumed by prompts and formatting."""

    owner = require_mapping(value.get("owner"), "owner")
    required_string(owner, "display_name", "owner")
    required_string(owner, "timezone", "owner")
    for key in ("roles", "interests"):
        _string_list(owner.get(key), f"owner.{key}")
    _string_list(value.get("rules"), "rules")


def validate_sources(value: dict[str, Any]) -> None:
    """Validate source-level settings without performing I/O."""

    http = require_mapping(value.get("http"), "http")
    required_string(http, "user_agent", "http")
    _string_list(http.get("allowed_hosts"), "http.allowed_hosts")
    timeout = http.get("timeout_seconds")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("http.timeout_seconds must be positive")
    collectors = require_mapping(value.get("collectors"), "collectors")
    for name, raw in collectors.items():
        row = require_mapping(raw, f"collectors.{name}")
        required_string(row, "type", f"collectors.{name}")


def validate_watchlist(value: dict[str, Any]) -> None:
    """Validate market watchlist and positive thresholds."""

    _string_list(value.get("tickers"), "tickers")
    _string_list(value.get("index_tickers"), "index_tickers")
    _string_list(value.get("context"), "context")
    thresholds = require_mapping(value.get("alert_thresholds"), "alert_thresholds")
    for key in ("stock_percent", "index_percent", "vix_jump_percent"):
        item = thresholds.get(key)
        if not isinstance(item, (int, float)) or item <= 0:
            raise ConfigError(f"alert_thresholds.{key} must be positive")
    _number_list(thresholds.get("vix_levels"), "alert_thresholds.vix_levels")
    _number_list(thresholds.get("circuit_breakers"), "alert_thresholds.circuit_breakers")


def validate_discord(value: dict[str, Any]) -> None:
    """Validate channel names without accepting numeric identifiers in examples."""

    required_string(value, "guild_name", "discord")
    channels = _string_list(value.get("channels"), "channels")
    if len(set(channels)) != len(channels):
        raise ConfigError("discord channels must be unique")
    required_string(value, "direct_message_alias", "discord")


def validate_limits(value: dict[str, Any]) -> None:
    """Validate that all configured numeric limits are positive."""

    for section, raw in value.items():
        mapping = require_mapping(raw, section)
        for key, item in mapping.items():
            if not isinstance(item, (int, float)) or item <= 0:
                raise ConfigError(f"{section}.{key} must be positive")


def validate_stack(value: dict[str, Any]) -> None:
    """Validate the config-level integration choices used by the composition root."""

    runtime = require_mapping(value.get("runtime"), "runtime")
    required_string(runtime, "type", "runtime")
    required_string(runtime, "interpreter", "runtime")
    model = require_mapping(value.get("model"), "model")
    required_string(model, "provider", "model")
    required_string(model, "base_url", "model")
    terminal = require_mapping(value.get("terminal"), "terminal")
    required_string(terminal, "backend", "terminal")
    required_string(terminal, "modal_mode", "terminal")
    notifier = require_mapping(value.get("notifier"), "notifier")
    required_string(notifier, "backend", "notifier")
    prefix = required_string(notifier, "target_prefix", "notifier")
    if ":" in prefix:
        raise ConfigError("notifier.target_prefix must not contain ':'")


def _string_list(value: object, context: str) -> list[str]:
    rows = require_list(value, context)
    if not all(isinstance(item, str) and item for item in rows):
        raise ConfigError(f"{context} must contain non-empty strings")
    return cast(list[str], rows)


def _number_list(value: object, context: str) -> list[float]:
    rows = require_list(value, context)
    if not all(isinstance(item, (int, float)) for item in rows):
        raise ConfigError(f"{context} must contain numbers")
    return [float(item) for item in rows]
