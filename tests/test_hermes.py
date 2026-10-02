import json
from pathlib import Path

import pytest

from saathi.adapters.hermes import create_command, edit_command, existing_jobs
from saathi.domain.models import JobSpec


def test_create_command_uses_script_and_interpreter_arguments() -> None:
    spec = JobSpec("news", "0 6 * * *", "ai_news", "ai.md", "ai", True)
    command = create_command(
        Path("/bin/hermes"),
        spec,
        "prompt",
        "discord:channel",
        "news.py",
        Path("/srv/venv/bin/python"),
    )
    assert command[:4] == ["/bin/hermes", "cron", "create", "0 6 * * *"]
    assert command[command.index("--script") + 1] == "news.py"
    assert "--no-agent" not in command


def test_edit_command_can_set_no_agent_mode() -> None:
    spec = JobSpec("health", "*/5 * * * *", "health", None, "ops", False)
    command = edit_command(
        Path("/bin/hermes"),
        "job-123",
        spec,
        "",
        "discord:channel",
        "health.py",
        Path("/srv/venv/bin/python"),
    )
    assert command[:4] == ["/bin/hermes", "cron", "edit", "job-123"]
    assert "--no-agent" in command
    assert "--prompt" not in command


def test_existing_jobs_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps({"jobs": [{"name": "same"}, {"name": "same"}]}))
    with pytest.raises(ValueError, match="duplicate Hermes job name"):
        existing_jobs(path)
