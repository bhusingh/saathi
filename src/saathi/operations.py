"""Composition helpers for setup, cron synchronization, and diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
from pathlib import Path
from typing import Any

from saathi.adapters.clock import SystemClock
from saathi.adapters.discord_api import DiscordApi, DiscordApiError, parse_allowed_users
from saathi.adapters.hermes import apply_commands, create_command, edit_command, existing_jobs
from saathi.adapters.http import UrllibHttpClient
from saathi.adapters.state_json import JsonStateStore
from saathi.domain.config import (
    ConfigError,
    ConfigPaths,
    load_jobs,
    load_yaml,
    require_mapping,
    validate_discord,
    validate_limits,
    validate_profile,
    validate_sources,
    validate_stack,
    validate_watchlist,
)
from saathi.domain.models import JobSpec
from saathi.jobs.registry import build_job


def source_dependencies(
    paths: ConfigPaths, state_dir: Path
) -> tuple[dict[str, Any], UrllibHttpClient, JsonStateStore]:
    """Compose configured HTTP and state adapters."""

    config = load_yaml(paths.named("sources"))
    http_config = require_mapping(config.get("http"), "http")
    raw_hosts = http_config.get("allowed_hosts")
    if not isinstance(raw_hosts, list) or not all(isinstance(host, str) for host in raw_hosts):
        raise ConfigError("http.allowed_hosts must be a list of host names")
    user_agent = http_config.get("user_agent")
    if not isinstance(user_agent, str) or not user_agent:
        raise ConfigError("http.user_agent must be a non-empty string")
    http = UrllibHttpClient(
        set(raw_hosts), user_agent, float(http_config.get("timeout_seconds", 20))
    )
    return config, http, JsonStateStore(state_dir)


def profile_timezone(paths: ConfigPaths) -> str:
    """Return the owner's display timezone."""

    profile = load_yaml(paths.named("profile"))
    owner = require_mapping(profile.get("owner"), "owner")
    timezone_name = owner.get("timezone", "UTC")
    return timezone_name if isinstance(timezone_name, str) else "UTC"


def discord_setup(paths: ConfigPaths, state_dir: Path) -> int:
    """Provision channels after verifying a fail-closed owner allowlist."""

    api = DiscordApi(os.environ.get("DISCORD_BOT_TOKEN", ""))
    guild_id = os.environ.get("DISCORD_GUILD_ID", "")
    owner = api.guild_owner(guild_id)
    try:
        allowed = parse_allowed_users(os.environ.get("DISCORD_ALLOWED_USERS", ""))
    except DiscordApiError as exc:
        raise DiscordApiError(f"{exc}; discovered guild owner ID: {owner}") from exc
    if owner not in allowed:
        raise DiscordApiError(
            "fail-closed: guild owner is not in DISCORD_ALLOWED_USERS; add the discovered numeric "
            f"owner ID ({owner}) to ~/.hermes/.env with mode 600, then rerun"
        )
    config = load_yaml(paths.named("discord"))
    names = config.get("channels")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ConfigError("discord channels must be a list of names")
    channels = api.ensure_text_channels(guild_id, names)
    channels[str(config.get("direct_message_alias", "direct-message"))] = api.create_dm(owner)
    JsonStateStore(state_dir).save("discord_channels", channels)
    print("Discord channels are ready; owner allowlist verified.")
    return 0


def jobs_sync(args: argparse.Namespace, paths: ConfigPaths, state_dir: Path) -> int:
    """Plan or apply an idempotent Hermes cron reconciliation."""

    specs = load_jobs(paths.named("jobs"))
    source_config = load_yaml(paths.named("sources"))
    stack_config = load_yaml(paths.named("stack"))
    validate_stack(stack_config)
    notifier = require_mapping(stack_config.get("notifier"), "notifier")
    runtime = require_mapping(stack_config.get("runtime"), "runtime")
    target_prefix = str(notifier["target_prefix"])
    interpreter = _resolve_from_project(paths, str(runtime["interpreter"]))
    collectors = require_mapping(source_config.get("collectors"), "collectors")
    for spec in specs:
        if (
            spec.collector is not None
            and spec.collector != "health"
            and spec.collector not in collectors
        ):
            raise ConfigError(f"job {spec.name!r} has unknown collector {spec.collector!r}")
    channels = JsonStateStore(state_dir).load("discord_channels")
    hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    executable = Path(os.environ.get("HERMES_BIN", str(Path.home() / ".local/bin/hermes")))
    current = existing_jobs(hermes_home / "cron/jobs.json")
    state_store = JsonStateStore(state_dir)
    manifest = state_store.load("jobs_manifest")
    commands: list[list[str]] = []
    next_manifest: dict[str, Any] = {}
    for spec in specs:
        deliver_id = channels.get(spec.channel)
        if not isinstance(deliver_id, str):
            raise ConfigError(f"channel {spec.channel!r} is not configured; run discord setup")
        prompt = _render_prompt(paths, spec.prompt_file, state_dir)
        script = f"saathi_{_safe_name(spec.name)}.py"
        delivery = f"{target_prefix}:{deliver_id}"
        desired = _job_fingerprint(spec, prompt, delivery, script, interpreter)
        next_manifest[spec.name] = desired
        if spec.name in current and manifest.get(spec.name) == desired:
            print(f"unchanged: {spec.name}")
            continue
        if spec.name in current:
            job_id = current[spec.name].get("id")
            if not isinstance(job_id, str) or not job_id:
                raise ConfigError(f"existing Hermes job {spec.name!r} has no valid id")
            commands.append(
                edit_command(
                    executable,
                    job_id,
                    spec,
                    prompt,
                    delivery,
                    script,
                    interpreter,
                )
            )
        else:
            commands.append(
                create_command(
                    executable,
                    spec,
                    prompt,
                    delivery,
                    script,
                    interpreter,
                )
            )
        print(f"{'update' if spec.name in current else 'create'}: {spec.name}")
    if args.apply:
        _write_collectors(specs, hermes_home / "scripts", paths.root, state_dir)
        apply_commands(commands)
        state_store.save("jobs_manifest", next_manifest)
        print(f"Applied {len(commands)} change(s).")
    else:
        print(f"Dry run: {len(commands)} change(s). Re-run with --apply to execute.")
    return 0


def _render_prompt(paths: ConfigPaths, filename: str | None, state_dir: Path | None = None) -> str:
    if filename is None:
        return ""
    profile = json.dumps(load_yaml(paths.named("profile")), indent=2)
    prompts = paths.root.resolve().parent / "prompts"
    try:
        template = (prompts / filename).read_text(encoding="utf-8")
        rules = (prompts / "rules.md").read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot load prompt: {exc}") from exc
    feedback_path = (state_dir or paths.root.resolve().parent / "state") / "feedback.md"
    try:
        feedback = (
            feedback_path.read_text(encoding="utf-8")
            if feedback_path.exists()
            else "No feedback yet."
        )
    except OSError as exc:
        raise ConfigError(f"cannot load feedback: {exc}") from exc
    return (
        template.replace("{profile}", profile)
        .replace("{rules}", rules)
        .replace("{feedback}", feedback)
    )


def _safe_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _resolve_from_project(paths: ConfigPaths, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (paths.root.resolve().parent / path).resolve()


def _job_fingerprint(
    spec: JobSpec, prompt: str, channel_id: str, script: str, interpreter: Path
) -> str:
    value = {
        "name": spec.name,
        "schedule": spec.schedule,
        "collector": spec.collector,
        "command": spec.command,
        "agent": spec.agent,
        "prompt": prompt,
        "channel": channel_id,
        "script": script,
        "interpreter": str(interpreter),
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _write_collectors(
    specs: list[JobSpec], scripts: Path, config_dir: Path, state_dir: Path
) -> None:
    scripts.mkdir(parents=True, exist_ok=True, mode=0o700)
    for spec in specs:
        path = scripts / f"saathi_{_safe_name(spec.name)}.py"
        arguments: list[str] = [
            "--config-dir",
            str(config_dir.resolve()),
            "--state-dir",
            str(state_dir.resolve()),
        ]
        if spec.collector is not None:
            arguments.extend(["collect", spec.collector])
        else:
            arguments.extend(spec.command)
        body = (
            f"from saathi.cli import main\n\nif __name__ == '__main__':\n    main({arguments!r})\n"
        )
        path.write_text(body, encoding="utf-8")
        path.chmod(0o700)


def doctor(paths: ConfigPaths, state_dir: Path) -> int:
    """Validate configuration, permissions, source composition, and proxy health."""

    problems: list[str] = []
    validators = {
        "profile": validate_profile,
        "sources": validate_sources,
        "watchlist": validate_watchlist,
        "discord": validate_discord,
        "limits": validate_limits,
        "stack": validate_stack,
    }
    for name, validator in validators.items():
        try:
            validator(load_yaml(paths.named(name)))
        except ConfigError as exc:
            problems.append(str(exc))
    try:
        load_jobs(paths.named("jobs"))
        source_config, http, state = source_dependencies(paths, state_dir)
        collectors = require_mapping(source_config.get("collectors"), "collectors")
        for name in collectors:
            build_job(name, collectors, http, state, SystemClock())
    except ConfigError as exc:
        problems.append(str(exc))
    env_path = Path.home() / ".hermes/.env"
    if env_path.exists() and env_path.stat().st_mode & 0o077:
        problems.append("~/.hermes/.env must be chmod 600")
    try:
        with socket.create_connection(("127.0.0.1", 8645), timeout=1):
            pass
    except OSError:
        problems.append("Hermes proxy is not reachable at 127.0.0.1:8645")
    if problems:
        print("Doctor found issues:\n" + "\n".join(f"- {problem}" for problem in problems))
        return 1
    print("Configuration, secret-file permissions, and loopback proxy look healthy.")
    return 0
