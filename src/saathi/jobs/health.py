"""Host-health checks for no-agent delivery."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def health_report(root: Path = Path("/")) -> str:
    """Return an empty string when healthy or a concise alert when unhealthy."""

    problems: list[str] = []
    usage = shutil.disk_usage(root)
    if usage.used / usage.total > 0.85:
        problems.append(f"disk {usage.used / usage.total:.0%} full")
    for unit in ("hermes-gateway", "hermes-proxy"):
        result = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.stdout.strip() != "active":
            problems.append(f"service {unit} is {result.stdout.strip() or 'unknown'}")
    if not problems:
        return ""
    return "**Hermes health check - attention needed**\n" + "\n".join(
        f"- {problem}" for problem in problems
    )
