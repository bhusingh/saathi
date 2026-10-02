"""Hermes cron command planning and execution."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from saathi.domain.models import JobSpec


def existing_jobs(path: Path) -> dict[str, dict[str, Any]]:
    """Load Hermes' local cron registry without executing shell commands."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    jobs = raw.get("jobs", []) if isinstance(raw, dict) else []
    values = jobs.values() if isinstance(jobs, dict) else jobs
    result: dict[str, dict[str, Any]] = {}
    for job in values:
        if not isinstance(job, dict) or not isinstance(job.get("name"), str):
            continue
        name = str(job["name"])
        if name in result:
            raise ValueError(f"duplicate Hermes job name: {name}")
        result[name] = job
    return result


def create_command(
    executable: Path,
    job: JobSpec,
    prompt: str,
    deliver: str,
    script: str | Path,
    interpreter: Path,
) -> list[str]:
    """Build an argument-list-only Hermes command."""

    command = [str(executable), "cron", "create", job.schedule]
    if job.agent:
        command.append(prompt)
    command.extend(
        [
            "--name",
            job.name,
            "--script",
            str(script),
            "--interpreter",
            str(interpreter),
            "--deliver",
            deliver,
        ]
    )
    if not job.agent:
        command.extend(["--no-agent", "--failure-deliver", "local"])
    return command


def edit_command(
    executable: Path,
    job_id: str,
    job: JobSpec,
    prompt: str,
    deliver: str,
    script: str | Path,
    interpreter: Path,
) -> list[str]:
    """Build a complete Hermes edit command for an existing named job."""

    command = [
        str(executable),
        "cron",
        "edit",
        job_id,
        "--schedule",
        job.schedule,
        "--script",
        str(script),
        "--interpreter",
        str(interpreter),
        "--deliver",
        deliver,
    ]
    if job.agent:
        command.extend(["--prompt", prompt, "--agent"])
    else:
        command.append("--no-agent")
    return command


def apply_commands(commands: list[list[str]]) -> None:
    """Execute reviewed cron commands without a shell."""

    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr[-500:] or f"command failed: {command[0]}")
