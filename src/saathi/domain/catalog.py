"""Validated capability and optional add-on catalog models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from saathi.domain.config import (
    ConfigError,
    load_yaml,
    require_list,
    require_mapping,
    required_string,
)


@dataclass(frozen=True, slots=True)
class Question:
    """A catalog-driven interview question."""

    id: str
    prompt: str
    kind: str
    default: object


@dataclass(frozen=True, slots=True)
class Capability:
    """A selectable bundle of collectors, jobs, prompts, and channels."""

    id: str
    title: str
    description: str
    questions: tuple[Question, ...]
    collectors: tuple[str, ...]
    jobs: tuple[dict[str, Any], ...]
    channels: tuple[str, ...]
    default_schedule: str
    addons: tuple[str, ...]
    cost: str
    privacy: str
    ram: str


@dataclass(frozen=True, slots=True)
class Addon:
    """Reviewed third-party software metadata; never an installation action."""

    id: str
    name: str
    url: str
    licence: str
    stars_date: str
    stars: int
    adds: str
    ram: str
    risks: str
    install_steps: tuple[str, ...]


def load_capabilities(path: Path) -> dict[str, Capability]:
    """Load and validate the capability catalog."""

    root = load_yaml(path)
    _schema_version(root, path)
    result: dict[str, Capability] = {}
    for index, value in enumerate(require_list(root.get("capabilities"), "capabilities")):
        context = f"capabilities[{index}]"
        row = require_mapping(value, context)
        capability_id = required_string(row, "id", context)
        if capability_id in result:
            raise ConfigError(f"duplicate capability id: {capability_id}")
        questions = tuple(
            _question(item, f"{context}.questions") for item in _rows(row, "questions")
        )
        if len({question.id for question in questions}) != len(questions):
            raise ConfigError(f"{context}.questions contains duplicate ids")
        jobs = tuple(require_mapping(item, f"{context}.jobs") for item in _rows(row, "jobs"))
        for job in jobs:
            required_string(job, "name", f"{context}.jobs")
            required_string(job, "channel", f"{context}.jobs")
            has_collector = isinstance(job.get("collector"), str)
            has_command = isinstance(job.get("command"), list)
            if has_collector == has_command:
                raise ConfigError(f"{context}.jobs must define exactly one execution mode")
            command = job.get("command")
            if has_command and (
                not isinstance(command, list)
                or not command
                or not all(isinstance(item, str) and item for item in command)
            ):
                raise ConfigError(f"{context}.jobs.command must contain non-empty strings")
            prompt = job.get("prompt_file")
            if prompt is not None and not isinstance(prompt, str):
                raise ConfigError(f"{context}.jobs.prompt_file must be a string or null")
            if not isinstance(job.get("agent"), bool):
                raise ConfigError(f"{context}.jobs.agent must be a boolean")
        result[capability_id] = Capability(
            id=capability_id,
            title=required_string(row, "title", context),
            description=required_string(row, "description", context),
            questions=questions,
            collectors=tuple(_strings(row, "collectors", context)),
            jobs=jobs,
            channels=tuple(_strings(row, "channels", context)),
            default_schedule=required_string(row, "default_schedule", context),
            addons=tuple(_strings(row, "addons", context)),
            cost=required_string(row, "cost", context),
            privacy=required_string(row, "privacy", context),
            ram=required_string(row, "ram", context),
        )
    return result


def load_addons(path: Path) -> dict[str, Addon]:
    """Load and validate vetted add-on metadata."""

    root = load_yaml(path)
    _schema_version(root, path)
    result: dict[str, Addon] = {}
    for index, value in enumerate(require_list(root.get("addons"), "addons")):
        context = f"addons[{index}]"
        row = require_mapping(value, context)
        addon_id = required_string(row, "id", context)
        if addon_id in result:
            raise ConfigError(f"duplicate add-on id: {addon_id}")
        url = required_string(row, "url", context)
        if not url.startswith("https://"):
            raise ConfigError(f"{context}.url must use https")
        stars = require_mapping(row.get("stars_as_of"), f"{context}.stars_as_of")
        count = stars.get("count")
        if not isinstance(count, int) or count < 0:
            raise ConfigError(f"{context}.stars_as_of.count must be a non-negative integer")
        result[addon_id] = Addon(
            id=addon_id,
            name=required_string(row, "name", context),
            url=url,
            licence=required_string(row, "licence", context),
            stars_date=required_string(stars, "date", f"{context}.stars_as_of"),
            stars=count,
            adds=required_string(row, "adds", context),
            ram=required_string(row, "ram", context),
            risks=required_string(row, "risks", context),
            install_steps=tuple(_strings(row, "install_steps", context)),
        )
    return result


def _schema_version(root: dict[str, Any], path: Path) -> None:
    if root.get("schema_version") != 1:
        raise ConfigError(f"{path}: unsupported schema_version")


def _rows(row: dict[str, Any], key: str) -> list[Any]:
    return require_list(row.get(key), key)


def _strings(row: dict[str, Any], key: str, context: str) -> list[str]:
    values = _rows(row, key)
    if not all(isinstance(value, str) and value for value in values):
        raise ConfigError(f"{context}.{key} must contain non-empty strings")
    return [str(value) for value in values]


def _question(value: object, context: str) -> Question:
    row = require_mapping(value, context)
    kind = required_string(row, "type", context)
    if kind not in {"text", "list"}:
        raise ConfigError(f"{context}.type must be text or list")
    default = row.get("default")
    if kind == "text" and not isinstance(default, str):
        raise ConfigError(f"{context}.default must be a string")
    if kind == "list" and (
        not isinstance(default, list) or not all(isinstance(item, str) for item in default)
    ):
        raise ConfigError(f"{context}.default must be a list of strings")
    return Question(
        id=required_string(row, "id", context),
        prompt=required_string(row, "prompt", context),
        kind=kind,
        default=default,
    )
