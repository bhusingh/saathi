"""Restricted stdlib HTTP adapter."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, cast
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class HostNotAllowedError(ValueError):
    """Raised before an undeclared outbound HTTP request."""


class ResponseTooLargeError(ValueError):
    """Raised when an HTTP response exceeds the configured byte cap."""


def _validate_url(url: str, hosts: set[str], *, redirect: bool = False) -> None:
    parts = urlsplit(url)
    label = "redirect " if redirect else ""
    if parts.scheme.lower() != "https":
        raise HostNotAllowedError(f"{label}URL must use https")
    host = (parts.hostname or "").lower()
    if host not in hosts:
        raise HostNotAllowedError(f"{label}host is not declared in config: {host or '<missing>'}")


class _AllowlistedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts: set[str]) -> None:
        self._hosts = hosts
        super().__init__()

    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        _validate_url(new_url, self._hosts, redirect=True)
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


class UrllibHttpClient:
    """HTTP client enforcing timeout, user agent, and a host allowlist."""

    def __init__(
        self,
        allowed_hosts: set[str],
        user_agent: str,
        timeout: float = 20.0,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> None:
        self._hosts = {host.lower() for host in allowed_hosts}
        self._user_agent = user_agent
        self._timeout = timeout
        self._max_response_bytes = max_response_bytes
        self._opener = urllib.request.build_opener(_AllowlistedRedirect(self._hosts))

    def get(self, url: str, *, accept: str | None = None) -> bytes:
        """Fetch bytes after checking the destination host."""

        _validate_url(url, self._hosts)
        headers = {"User-Agent": self._user_agent}
        if accept:
            headers["Accept"] = accept
        request = urllib.request.Request(url, headers=headers)
        with self._opener.open(request, timeout=self._timeout) as response:
            content = bytes(response.read(self._max_response_bytes + 1))
        if len(content) > self._max_response_bytes:
            raise ResponseTooLargeError(f"response exceeds {self._max_response_bytes} byte limit")
        return content

    def get_json(self, url: str) -> Any:
        """Fetch and decode JSON."""

        return cast(Any, json.loads(self.get(url, accept="application/json")))
