"""Pure models and safety policy for guided configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from saathi.domain.config import ConfigError

_SECRET_WORDS = re.compile(
    r"\b(api[- ]?key|token|password|secret|credential|private key)\b", re.IGNORECASE
)
_INSTALL_WORDS = re.compile(
    r"\b(install|pip\s+install|uv\s+add|git\s+clone|clone\s+(?:a\s+)?repo|add[- ]?on)\b",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://[^\s<>'\"]+")


@dataclass(frozen=True, slots=True)
class InitPlan:
    """A complete, reviewable set of configuration file replacements."""

    files: dict[str, dict[str, Any]]
    selected_capabilities: tuple[str, ...]
    selected_addons: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChangePlan:
    """A staged configuration change with optimistic-lock snapshots."""

    id: str
    request: str
    created_at: str
    before: dict[str, dict[str, Any]]
    after: dict[str, dict[str, Any]]
    diff: str


def validate_change_request(request: str) -> None:
    """Reject requests that configuration chat must never carry out."""

    if _SECRET_WORDS.search(request):
        raise ConfigError(
            "secrets cannot be added through chat or config; enter them with hidden input "
            "and store "
            "them in ~/.hermes/.env with mode 600"
        )
    if _INSTALL_WORDS.search(request):
        raise ConfigError(
            "chat configuration never installs code or repositories; review "
            "catalog/addons.yaml and "
            "run an install command yourself"
        )
    for value in _URL.findall(request):
        if urlsplit(value).scheme.lower() != "https":
            raise ConfigError("source URLs added through chat must use https")


def https_host(url: str) -> str:
    """Validate a public HTTPS URL and return its normalized host."""

    parts = urlsplit(url)
    if parts.scheme.lower() != "https" or not parts.hostname or parts.username or parts.password:
        raise ConfigError("source URLs must use https and must not contain credentials")
    if parts.port not in {None, 443}:
        raise ConfigError("source URLs may only use the default HTTPS port")
    return parts.hostname.lower()
