from pathlib import Path

import pytest

from saathi.domain.config import (
    ConfigError,
    load_jobs,
    load_yaml,
    validate_discord,
    validate_limits,
    validate_profile,
    validate_sources,
    validate_stack,
    validate_watchlist,
)

ROOT = Path(__file__).parents[1]


def test_every_example_yaml_loads() -> None:
    files = sorted((ROOT / "config").glob("*.example.yaml"))
    assert files
    for path in files:
        assert isinstance(load_yaml(path), dict)


def test_every_example_schema_validates() -> None:
    config = ROOT / "config"
    validate_profile(load_yaml(config / "profile.example.yaml"))
    validate_sources(load_yaml(config / "sources.example.yaml"))
    validate_watchlist(load_yaml(config / "watchlist.example.yaml"))
    validate_discord(load_yaml(config / "discord.example.yaml"))
    validate_limits(load_yaml(config / "limits.example.yaml"))
    validate_stack(load_yaml(config / "stack.example.yaml"))


def test_example_jobs_validate() -> None:
    jobs = load_jobs(ROOT / "config/jobs.example.yaml")
    assert jobs[0].name == "agent health"
    assert len({job.name for job in jobs}) == len(jobs)


def test_duplicate_jobs_fail_clearly(tmp_path: Path) -> None:
    path = tmp_path / "jobs.yaml"
    path.write_text(
        "jobs:\n"
        "  - {name: same, schedule: '* * * * *', collector: one, channel: x}\n"
        "  - {name: same, schedule: '* * * * *', collector: two, channel: x}\n"
    )
    with pytest.raises(ConfigError, match="duplicate job"):
        load_jobs(path)


def test_job_command_is_an_argument_list_and_excludes_collector(tmp_path: Path) -> None:
    path = tmp_path / "jobs.yaml"
    path.write_text(
        "jobs:\n  - {name: market, schedule: '* * * * *', command: [markets, brief], channel: x}\n"
    )
    job = load_jobs(path)[0]
    assert job.collector is None
    assert job.command == ("markets", "brief")


def test_job_requires_exactly_one_execution_mode(tmp_path: Path) -> None:
    path = tmp_path / "jobs.yaml"
    path.write_text(
        "jobs:\n"
        "  - name: invalid\n"
        "    schedule: '* * * * *'\n"
        "    collector: one\n"
        "    command: [markets, brief]\n"
        "    channel: x\n"
    )
    with pytest.raises(ConfigError, match="exactly one"):
        load_jobs(path)


def test_unsafe_yaml_is_not_constructed(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.yaml"
    path.write_text("!!python/object/apply:os.system ['false']")
    with pytest.raises(ConfigError):
        load_yaml(path)
