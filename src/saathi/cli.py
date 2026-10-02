"""Command-line composition root for Saathi."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import cast

from saathi.adapters.change_files import YamlChangeRepository
from saathi.adapters.clock import SystemClock
from saathi.adapters.config_files import YamlConfigRepository
from saathi.adapters.discord_api import DiscordApiError
from saathi.adapters.discovery import CatalogDiscovery
from saathi.adapters.http import UrllibHttpClient
from saathi.adapters.state_json import DeferredStateStore
from saathi.domain.catalog import Capability, load_addons, load_capabilities
from saathi.domain.config import ConfigError, ConfigPaths, load_yaml, require_mapping
from saathi.domain.formatting import format_sheet
from saathi.domain.models import Sheet
from saathi.jobs.health import health_report
from saathi.jobs.registry import build_job
from saathi.market_cli import run_market, valid_ticker
from saathi.operations import (
    discord_setup,
    doctor,
    jobs_sync,
    profile_timezone,
    source_dependencies,
)
from saathi.use_cases.config_changes import apply_change, propose_change, undo_latest
from saathi.use_cases.feedback import record_feedback
from saathi.use_cases.setup import apply_init_plan, build_init_plan, render_init_plan


def parser() -> argparse.ArgumentParser:
    """Build the public command-line grammar."""

    root = argparse.ArgumentParser(prog="saathi")
    root.add_argument("--config-dir", type=Path, default=Path("config"))
    root.add_argument("--state-dir", type=Path, default=Path("state"))
    root.add_argument("--catalog-dir", type=Path, default=Path("catalog"))
    commands = root.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init", help="guided, catalog-driven setup")
    initialize.add_argument("--answers", type=Path, help="non-interactive YAML answers")
    initialize.add_argument("--yes", action="store_true", help="approve the displayed plan")
    collect = commands.add_parser("collect", help="run a configured collector")
    collect.add_argument("job")
    markets = commands.add_parser("markets", help="deterministic market research")
    market_commands = markets.add_subparsers(dest="market_command", required=True)
    market_commands.add_parser("brief")
    fundamentals = market_commands.add_parser("fundamentals")
    fundamentals.add_argument("tickers", nargs="+", type=valid_ticker)
    market_commands.add_parser("alerts")
    macro = market_commands.add_parser("macro")
    macro.add_argument("period", choices=("week",))
    deep = market_commands.add_parser("deep-dive")
    deep.add_argument("ticker", type=valid_ticker)
    deep.add_argument("--date", type=date.fromisoformat, default=date.today())
    commands.add_parser("doctor", help="validate configuration and local services")
    discord = commands.add_parser("discord", help="configure Discord")
    discord.add_subparsers(dest="discord_command", required=True).add_parser("setup")
    jobs = commands.add_parser("jobs", help="synchronize Hermes schedules")
    sync = jobs.add_subparsers(dest="jobs_command", required=True).add_parser("sync")
    sync.add_argument("--apply", action="store_true", help="execute; default is dry-run")
    config = commands.add_parser("config", help="propose and approve chat-driven changes")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    propose = config_commands.add_parser("propose")
    propose.add_argument("request")
    apply = config_commands.add_parser("apply")
    apply.add_argument("change_id")
    config_commands.add_parser("undo")
    feedback = commands.add_parser("feedback", help="record owner output preferences")
    feedback_commands = feedback.add_subparsers(dest="feedback_command", required=True)
    record = feedback_commands.add_parser("record")
    record.add_argument("message")
    return root


def _paths(args: argparse.Namespace) -> tuple[ConfigPaths, Path]:
    return ConfigPaths(cast(Path, args.config_dir)), cast(Path, args.state_dir)


def _init(args: argparse.Namespace, paths: ConfigPaths) -> int:
    catalog_dir = cast(Path, args.catalog_dir)
    capabilities = load_capabilities(catalog_dir / "capabilities.yaml")
    addons = load_addons(catalog_dir / "addons.yaml")
    answers_path = cast(Path | None, args.answers)
    answers = load_yaml(answers_path) if answers_path is not None else _interview(capabilities)
    repository = YamlConfigRepository(paths.root)
    discovery = None
    if bool(answers.get("discover", False)):
        http = UrllibHttpClient(
            {"api.github.com", "itunes.apple.com", "www.youtube.com"},
            "Saathi/0.1 setup discovery",
        )
        discovery = CatalogDiscovery(http, catalog_dir / "discovery.yaml")
    plan = build_init_plan(repository, capabilities, addons, answers, discovery)
    print(render_init_plan(plan, repository, addons))
    approved = bool(args.yes) or answers.get("approved") is True
    if not approved:
        try:
            approved = input("Apply this plan? Type yes to write config: ").strip().lower() == "yes"
        except EOFError as exc:
            raise ConfigError("approval required; rerun interactively or pass --yes") from exc
    if not approved:
        print("Plan not applied.")
        return 1
    apply_init_plan(plan, repository)
    print("Configuration written with mode 0600.")
    print("Next (optional): saathi discord setup")
    print("Then preview/apply schedules: saathi jobs sync; saathi jobs sync --apply")
    return 0


def _interview(capabilities: dict[str, Capability]) -> dict[str, object]:
    print("Saathi guided setup. No secret will be requested or written to config.")
    profile = input("Who are you? (one paragraph): ").strip()
    print("Capabilities:")
    for capability in capabilities.values():
        print(f"  {capability.id}: {capability.title} — {capability.description}")
    raw_selected = input("Choose capability IDs (comma-separated): ")
    selected = [value.strip() for value in raw_selected.split(",") if value.strip()]
    answers: dict[str, object] = {
        "profile": profile,
        "capabilities": selected,
        "display_name": input("Display name [the owner]: ").strip() or "the owner",
        "timezone": input("Timezone [UTC]: ").strip() or "UTC",
        "chat_app": input("Chat app [discord]: ").strip() or "discord",
        "privacy": input("Privacy [balanced/local]: ").strip() or "balanced",
    }
    languages = input("Output languages [English]: ").strip() or "English"
    answers["languages"] = [part.strip() for part in languages.split(",") if part.strip()]
    schedules: dict[str, str] = {}
    for capability_id in selected:
        selected_capability = capabilities.get(capability_id)
        if selected_capability is None:
            continue
        for question in selected_capability.questions:
            if question.id in answers:
                continue
            default = (
                ", ".join(question.default)
                if isinstance(question.default, list)
                else str(question.default)
            )
            value = input(f"{question.prompt} [{default}]: ").strip()
            if question.kind == "list":
                answers[question.id] = [
                    part.strip() for part in (value or default).split(",") if part.strip()
                ]
            else:
                answers[question.id] = value or default
        schedule = input(
            f"Schedule for {selected_capability.title} [{selected_capability.default_schedule}]: "
        ).strip()
        schedules[capability_id] = schedule or selected_capability.default_schedule
    answers["schedules"] = schedules
    return answers


def _config_change(args: argparse.Namespace, paths: ConfigPaths, state_dir: Path) -> int:
    catalog_dir = cast(Path, args.catalog_dir)
    capabilities = load_capabilities(catalog_dir / "capabilities.yaml")
    repository = YamlConfigRepository(paths.root)
    changes = YamlChangeRepository(state_dir)
    now = SystemClock().now()
    if args.config_command == "propose":
        change_id, diff = propose_change(args.request, repository, changes, capabilities, now)
        print(diff)
        print(f"Change ID: {change_id}")
        print(f"After owner approval: saathi config apply {change_id}")
    elif args.config_command == "apply":
        diff = apply_change(args.change_id, repository, changes, now)
        print(diff)
        print(f"Applied {args.change_id}. Undo with: saathi config undo")
    else:
        change_id, diff = undo_latest(repository, changes, now)
        print(diff)
        print(f"Undid {change_id}.")
    return 0


def _collect(args: argparse.Namespace, paths: ConfigPaths, state_dir: Path) -> int:
    if args.job == "health":
        report = health_report()
        if report:
            print(report)
        return 0
    config, http, durable_state = source_dependencies(paths, state_dir)
    state = DeferredStateStore(durable_state)
    collectors = require_mapping(config.get("collectors"), "collectors")
    sheet = build_job(args.job, collectors, http, state, SystemClock()).run()
    _write_collection_result(sheet, profile_timezone(paths), state)
    return 0


def _write_collection_result(sheet: Sheet, timezone_name: str, state: DeferredStateStore) -> None:
    """Write reportable data, log source errors, then commit collector state."""

    for error in sheet.errors:
        print(f"source unavailable: {error.source} - {error.reason}", file=sys.stderr)
    if sheet.sections:
        print(format_sheet(replace(sheet, errors=()), timezone_name), flush=True)
    state.commit()


def main(argv: list[str] | None = None) -> None:
    """Run the selected command and convert expected failures to concise messages."""

    args = parser().parse_args(argv)
    paths, state_dir = _paths(args)
    try:
        if args.command == "collect":
            code = _collect(args, paths, state_dir)
        elif args.command == "init":
            code = _init(args, paths)
        elif args.command == "markets":
            code = run_market(args, paths, state_dir)
        elif args.command == "doctor":
            code = doctor(paths, state_dir)
        elif args.command == "discord":
            code = discord_setup(paths, state_dir)
        elif args.command == "config":
            code = _config_change(args, paths, state_dir)
        elif args.command == "feedback":
            path = record_feedback(state_dir, args.message, SystemClock().now())
            print(f"Recorded preference in {path}.")
            code = 0
        else:
            code = jobs_sync(args, paths, state_dir)
    except (ConfigError, DiscordApiError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = 2
    raise SystemExit(code)
