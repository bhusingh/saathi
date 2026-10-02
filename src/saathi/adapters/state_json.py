"""Atomic JSON state and reusable deduplication."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

from saathi.domain.ports import Clock, StateStore


class JsonStateStore:
    """Keep namespaced state as owner-readable JSON files."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _path(self, namespace: str) -> Path:
        if not namespace.replace("_", "").replace("-", "").isalnum():
            raise ValueError("invalid state namespace")
        return self._root / f"{namespace}.json"

    def load(self, namespace: str) -> dict[str, Any]:
        """Read a namespace, treating missing state as empty."""

        try:
            value = json.loads(self._path(namespace).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return cast(dict[str, Any], value) if isinstance(value, dict) else {}

    def save(self, namespace: str, value: dict[str, Any]) -> None:
        """Atomically persist a namespace with private permissions."""

        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self._path(namespace)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, target)


class DeferredStateStore:
    """Stage state writes until stdout has been written successfully."""

    def __init__(self, store: StateStore) -> None:
        self._store = store
        self._pending: dict[str, dict[str, Any]] = {}

    def load(self, namespace: str) -> dict[str, Any]:
        """Read staged state first, otherwise the durable store."""

        value = self._pending.get(namespace)
        return deepcopy(value) if value is not None else self._store.load(namespace)

    def save(self, namespace: str, value: dict[str, Any]) -> None:
        """Stage a defensive copy of a namespace."""

        self._pending[namespace] = deepcopy(value)

    def commit(self) -> None:
        """Persist staged namespaces after successful output."""

        for namespace, value in self._pending.items():
            self._store.save(namespace, value)
        self._pending.clear()


class DedupeStore:
    """Remember canonical item keys for a bounded retention period."""

    def __init__(
        self, store: StateStore, namespace: str, clock: Clock, retention_days: int = 21
    ) -> None:
        self._store = store
        self._namespace = f"seen_{namespace}"
        self._retention = retention_days
        self._today = clock.today()
        cutoff = (self._today - timedelta(days=retention_days)).isoformat()
        self._values = {
            key: value
            for key, value in store.load(self._namespace).items()
            if isinstance(value, str) and value >= cutoff
        }

    def is_new(self, key: str) -> bool:
        """Return true once per retained key."""

        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        if digest in self._values:
            return False
        self._values[digest] = self._today.isoformat()
        return True

    def save(self) -> None:
        """Persist all keys observed by this instance."""

        self._store.save(self._namespace, self._values)
