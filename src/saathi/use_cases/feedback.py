"""Record owner feedback as prompt preferences, never as source facts."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from saathi.domain.config import ConfigError


def record_feedback(state_dir: Path, message: str, now: datetime) -> Path:
    """Append a private timestamped preference to state/feedback.md."""

    cleaned = " ".join(message.strip().splitlines())
    if not cleaned:
        raise ConfigError("feedback must not be empty")
    if len(cleaned) > 2000:
        raise ConfigError("feedback must be 2000 characters or fewer")
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = state_dir / "feedback.md"
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(f"- {now.isoformat()}: {cleaned}\n")
    os.chmod(path, 0o600)
    return path
