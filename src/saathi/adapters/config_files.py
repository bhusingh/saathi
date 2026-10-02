"""Filesystem adapter for owner configuration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from saathi.domain.config import ConfigError, load_yaml


class YamlConfigRepository:
    """Read templates and atomically write private YAML files."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def read(self, name: str) -> dict[str, Any] | None:
        """Read a generated config file when it exists."""

        path = self.root / f"{name}.yaml"
        return load_yaml(path) if path.exists() else None

    def read_template(self, name: str) -> dict[str, Any]:
        """Read a checked-in example as the generation base."""

        return load_yaml(self.root / f"{name}.example.yaml")

    def write(self, files: dict[str, dict[str, Any]]) -> None:
        """Atomically replace the requested files with mode 0600."""

        self.root.mkdir(parents=True, exist_ok=True)
        for name, value in files.items():
            allowed = {"discord", "jobs", "limits", "profile", "sources", "stack", "watchlist"}
            if name not in allowed:
                raise ConfigError(f"refusing to write unknown config file: {name}")
            target = self.root / f"{name}.yaml"
            descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=self.root)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    yaml.safe_dump(value, stream, sort_keys=False, allow_unicode=True)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, 0o600)
                os.replace(temporary, target)
            except BaseException:
                Path(temporary).unlink(missing_ok=True)
                raise
