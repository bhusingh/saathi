from pathlib import Path

import pytest

from saathi.domain.config import ConfigPaths
from saathi.domain.models import JobSpec
from saathi.operations import _job_fingerprint, _render_prompt, _write_collectors


def test_prompts_resolve_from_configured_project_not_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    config = project / "config"
    prompts = project / "prompts"
    config.mkdir(parents=True)
    prompts.mkdir()
    (config / "profile.yaml").write_text("owner: {display_name: Test}\n")
    (prompts / "rules.md").write_text("RULES")
    (prompts / "report.md").write_text("{rules}\n{profile}")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    rendered = _render_prompt(ConfigPaths(config), "report.md")
    assert rendered.startswith("RULES")
    assert '"display_name": "Test"' in rendered


def test_command_job_generates_arbitrary_saathi_arguments(tmp_path: Path) -> None:
    spec = JobSpec(
        "market brief",
        "0 6 * * 1-5",
        None,
        None,
        "markets",
        False,
        ("markets", "brief"),
    )
    scripts = tmp_path / "scripts"
    _write_collectors([spec], scripts, tmp_path / "config", tmp_path / "state")
    body = (scripts / "saathi_market_brief.py").read_text()
    assert "'markets', 'brief'" in body


def test_job_fingerprint_covers_script_and_interpreter() -> None:
    spec = JobSpec("news", "0 6 * * *", "ai_news", "ai.md", "ai")
    first = _job_fingerprint(spec, "prompt", "discord:1", "one.py", Path("/venv/python"))
    assert first != _job_fingerprint(spec, "prompt", "discord:1", "two.py", Path("/venv/python"))
    assert first != _job_fingerprint(spec, "prompt", "discord:1", "one.py", Path("/other/python"))
