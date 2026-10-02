"""Least-privilege Discord REST setup adapter."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, cast

DISCORD_API = "https://discord.com/api/v10"
SNOWFLAKE = re.compile(r"^[0-9]{15,22}$")


class DiscordApiError(RuntimeError):
    """Raised when Discord setup cannot safely continue."""


class DiscordApi:
    """Small bot-authenticated client for guild setup."""

    def __init__(self, token: str, timeout: float = 20.0) -> None:
        if not token:
            raise DiscordApiError("DISCORD_BOT_TOKEN is required")
        self._token = token
        self._timeout = timeout

    def _request(self, method: str, path: str, body: dict[str, object] | None = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            DISCORD_API + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bot {self._token}",
                "Content-Type": "application/json",
                "User-Agent": "Saathi/0.1 (+https://github.com/bhusingh/saathi)",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            raise DiscordApiError(f"Discord API {exc.code}: {detail}") from exc
        return json.loads(raw) if raw else None

    def guild_owner(self, guild_id: str) -> str:
        """Discover the numeric guild owner ID used for fail-closed allowlisting."""

        _require_snowflake(guild_id, "guild ID")
        data = self._request("GET", f"/guilds/{guild_id}")
        if not isinstance(data, dict) or not isinstance(data.get("owner_id"), str):
            raise DiscordApiError("Discord did not return a guild owner")
        return cast(str, data["owner_id"])

    def ensure_text_channels(self, guild_id: str, names: list[str]) -> dict[str, str]:
        """Create missing text channels and return name-to-ID mappings."""

        _require_snowflake(guild_id, "guild ID")
        current = self._request("GET", f"/guilds/{guild_id}/channels")
        if not isinstance(current, list):
            raise DiscordApiError("Discord returned an invalid channel list")
        channels = {
            str(row["name"]): str(row["id"])
            for row in current
            if isinstance(row, dict) and row.get("type") == 0 and "name" in row and "id" in row
        }
        for name in names:
            if name in channels:
                continue
            created = self._request(
                "POST", f"/guilds/{guild_id}/channels", {"name": name, "type": 0}
            )
            if not isinstance(created, dict) or not isinstance(created.get("id"), str):
                raise DiscordApiError(f"Discord did not create channel {name}")
            channels[name] = created["id"]
        return {name: channels[name] for name in names}

    def create_dm(self, owner_id: str) -> str:
        """Create or retrieve a direct-message channel with the owner."""

        _require_snowflake(owner_id, "owner ID")
        data = self._request("POST", "/users/@me/channels", {"recipient_id": owner_id})
        if not isinstance(data, dict) or not isinstance(data.get("id"), str):
            raise DiscordApiError("Discord did not return a DM channel")
        return cast(str, data["id"])


def _require_snowflake(value: str, label: str) -> None:
    if not SNOWFLAKE.fullmatch(value):
        raise DiscordApiError(f"invalid numeric Discord {label}")


def parse_allowed_users(value: str) -> set[str]:
    """Parse a non-empty comma-separated allowlist and discard blank fields."""

    users = {item.strip() for item in value.split(",") if item.strip()}
    if not users:
        raise DiscordApiError("DISCORD_ALLOWED_USERS must contain at least one numeric user ID")
    for user in users:
        _require_snowflake(user, "allowed user ID")
    return users
