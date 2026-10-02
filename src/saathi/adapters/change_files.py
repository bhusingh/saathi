"""Private YAML audit records for proposed configuration changes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from saathi.domain.config import ConfigError, load_yaml


class YamlChangeRepository:
    """Store one auditable record per change under state/changes."""

    def __init__(self, state_dir: Path) -> None:
        self._root = state_dir / "changes"

    def save(self, change_id: str, value: dict[str, Any]) -> None:
        """Atomically write a private change record."""

        allowed = "abcdefghijklmnopqrstuvwxyz0123456789-_"
        if not change_id or any(character not in allowed for character in change_id):
            raise ConfigError("invalid change id")
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self._root / f"{change_id}.yaml"
        descriptor, temporary = tempfile.mkstemp(prefix=".change.", dir=self._root)
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

    def load(self, change_id: str) -> dict[str, Any]:
        """Load a named record or fail clearly."""

        path = self._root / f"{change_id}.yaml"
        if not path.exists():
            raise ConfigError(f"unknown change id: {change_id}")
        return load_yaml(path)

    def list(self) -> list[dict[str, Any]]:
        """Load all records in lexical order."""

        if not self._root.exists():
            return []
        return [load_yaml(path) for path in sorted(self._root.glob("*.yaml"))]
