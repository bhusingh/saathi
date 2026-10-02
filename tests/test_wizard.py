from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from saathi.adapters.change_files import YamlChangeRepository
from saathi.adapters.config_files import YamlConfigRepository
from saathi.cli import main
from saathi.domain.catalog import load_addons, load_capabilities
from saathi.domain.config import ConfigError, load_jobs, load_yaml, validate_sources
from saathi.use_cases.config_changes import apply_change, propose_change, undo_latest
from saathi.use_cases.setup import apply_init_plan, build_init_plan

ROOT = Path(__file__).parents[1]
EXPECTED_CAPABILITIES = {
    "ai_news",
    "github_trending",
    "ai_engineering",
    "creator_radar",
    "content_ideas",
    "linkedin_drafts",
    "reel_scripts",
    "youtube_package",
    "industry_signals",
    "recalls",
    "policy_watch",
    "markets_brief",
    "markets_alerts",
    "macro_calendar",
    "fundamentals",
    "deep_dive",
    "daily_agenda",
    "weekly_review",
    "feedback",
    "health",
}


def _config_templates(tmp_path: Path) -> Path:
    config = tmp_path / "config"
    config.mkdir()
    for source in (ROOT / "config").glob("*.example.yaml"):
        shutil.copyfile(source, config / source.name)
    return config


def _initialize(tmp_path: Path) -> tuple[Path, Path]:
    config = _config_templates(tmp_path)
    state = tmp_path / "state"
    answers = tmp_path / "answers.yaml"
    answers.write_text(
        yaml.safe_dump(
            {
                "profile": "I build reliable AI products and want concise cited reports.",
                "display_name": "Test Owner",
                "capabilities": ["ai_news", "fundamentals", "health"],
                "timezone": "America/Vancouver",
                "chat_app": "discord",
                "privacy": "balanced",
                "topics": ["robotics"],
                "tickers": ["NVDA", "MSFT"],
                "approved": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "--config-dir",
                str(config),
                "--state-dir",
                str(state),
                "--catalog-dir",
                str(ROOT / "catalog"),
                "init",
                "--answers",
                str(answers),
            ]
        )
    assert raised.value.code == 0
    return config, state


def test_catalogs_validate_and_cover_requested_capabilities() -> None:
    capabilities = load_capabilities(ROOT / "catalog/capabilities.yaml")
    addons = load_addons(ROOT / "catalog/addons.yaml")
    assert set(capabilities) == EXPECTED_CAPABILITIES
    assert {addon for capability in capabilities.values() for addon in capability.addons} <= set(
        addons
    )
    for addon in addons.values():
        assert addon.url.startswith("https://")
        assert addon.install_steps


def test_init_answers_file_writes_expected_private_configs(tmp_path: Path) -> None:
    config, _ = _initialize(tmp_path)
    profile = load_yaml(config / "profile.yaml")
    sources = load_yaml(config / "sources.yaml")
    jobs = load_yaml(config / "jobs.yaml")["jobs"]
    assert profile["owner"]["profile"].startswith("I build reliable")
    assert profile["capabilities"] == ["ai_news", "fundamentals", "health"]
    assert set(sources["collectors"]) == {"ai_news"}
    assert ["markets", "fundamentals", "NVDA", "MSFT"] in [row.get("command") for row in jobs]
    assert all(
        (config / f"{name}.yaml").stat().st_mode & 0o777 == 0o600
        for name in (
            "profile",
            "sources",
            "watchlist",
            "jobs",
            "discord",
            "limits",
            "stack",
        )
    )


def test_every_capability_composes_valid_jobs_and_sources(tmp_path: Path) -> None:
    config = _config_templates(tmp_path)
    repository = YamlConfigRepository(config)
    capabilities = load_capabilities(ROOT / "catalog/capabilities.yaml")
    plan = build_init_plan(
        repository,
        capabilities,
        load_addons(ROOT / "catalog/addons.yaml"),
        {
            "profile": "I want all available reports for a composition test.",
            "capabilities": list(capabilities),
            "tickers": ["NVDA"],
            "privacy": "local",
            "chat_app": "discord",
        },
    )
    apply_init_plan(plan, repository)
    jobs = load_jobs(config / "jobs.yaml")
    validate_sources(load_yaml(config / "sources.yaml"))
    assert len(jobs) == len({job.name for job in jobs})
    assert all(
        job.prompt_file is None or (ROOT / "prompts" / job.prompt_file).exists() for job in jobs
    )


def test_propose_apply_undo_round_trip(tmp_path: Path) -> None:
    config, state = _initialize(tmp_path)
    repository = YamlConfigRepository(config)
    changes = YamlChangeRepository(state)
    capabilities = load_capabilities(ROOT / "catalog/capabilities.yaml")
    original = load_yaml(config / "watchlist.yaml")
    change_id, diff = propose_change(
        "add AAPL",
        repository,
        changes,
        capabilities,
        datetime(2026, 10, 2, 12, tzinfo=UTC),
    )
    assert "+- AAPL" in diff
    assert load_yaml(config / "watchlist.yaml") == original
    apply_change(
        change_id,
        repository,
        changes,
        datetime(2026, 10, 2, 12, 1, tzinfo=UTC),
    )
    assert "AAPL" in load_yaml(config / "watchlist.yaml")["tickers"]
    undone_id, undo_diff = undo_latest(
        repository, changes, datetime(2026, 10, 2, 12, 2, tzinfo=UTC)
    )
    assert undone_id == change_id
    assert "AAPL" in undo_diff
    assert load_yaml(config / "watchlist.yaml") == original
    assert changes.load(change_id)["status"] == "undone"


@pytest.mark.parametrize(
    ("change_request", "message"),
    [
        ("add my API key abc", "secrets cannot"),
        ("add http://example.com/feed.xml", "must use https"),
        ("install TradingAgents", "never installs"),
        ("git clone https://github.com/example/repo", "never installs"),
    ],
)
def test_chat_change_refusal_paths(tmp_path: Path, change_request: str, message: str) -> None:
    config, state = _initialize(tmp_path)
    with pytest.raises(ConfigError, match=message):
        propose_change(
            change_request,
            YamlConfigRepository(config),
            YamlChangeRepository(state),
            load_capabilities(ROOT / "catalog/capabilities.yaml"),
            datetime(2026, 10, 2, tzinfo=UTC),
        )


def test_https_feed_host_is_staged_with_source(tmp_path: Path) -> None:
    config, state = _initialize(tmp_path)
    repository = YamlConfigRepository(config)
    change_id, diff = propose_change(
        "add https://feeds.example.org/robotics.xml",
        repository,
        YamlChangeRepository(state),
        load_capabilities(ROOT / "catalog/capabilities.yaml"),
        datetime(2026, 10, 2, tzinfo=UTC),
    )
    assert "feeds.example.org" in diff
    assert "robotics.xml" in diff
    assert change_id.startswith("chg-")


def test_cron_bootstrap_removes_all_tools() -> None:
    script = (ROOT / "deploy/bootstrap/configure-free-models.sh").read_text(encoding="utf-8")
    assert "platform_toolsets.cron '[]'" in script
