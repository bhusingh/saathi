import urllib.request
from typing import Any

import pytest

from saathi.adapters.http import (
    HostNotAllowedError,
    ResponseTooLargeError,
    UrllibHttpClient,
    _AllowlistedRedirect,
)


def test_client_rejects_undeclared_host_before_network() -> None:
    client = UrllibHttpClient({"allowed.example"}, "test-agent")
    with pytest.raises(HostNotAllowedError, match="not declared"):
        client.get("https://blocked.example/data")


def test_client_rejects_plain_http_even_for_allowed_host() -> None:
    client = UrllibHttpClient({"allowed.example"}, "test-agent")
    with pytest.raises(HostNotAllowedError, match="https"):
        client.get("http://allowed.example/data")


def test_redirect_handler_rejects_undeclared_destination() -> None:
    handler = _AllowlistedRedirect({"allowed.example"})
    with pytest.raises(HostNotAllowedError, match="redirect"):
        handler.redirect_request(
            urllib.request.Request("https://allowed.example"),
            None,
            302,
            "Found",
            {},
            "https://blocked.example/data",
        )


def test_redirect_handler_rejects_https_downgrade() -> None:
    handler = _AllowlistedRedirect({"allowed.example"})
    with pytest.raises(HostNotAllowedError, match="https"):
        handler.redirect_request(
            urllib.request.Request("https://allowed.example"),
            None,
            302,
            "Found",
            {},
            "http://allowed.example/data",
        )


def test_response_size_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def read(self, size: int) -> bytes:
            return b"x" * size

    class Opener:
        def open(self, request: urllib.request.Request, *, timeout: float) -> Any:
            return Response()

    client = UrllibHttpClient({"allowed.example"}, "test-agent", max_response_bytes=10)
    monkeypatch.setattr(client, "_opener", Opener())
    with pytest.raises(ResponseTooLargeError, match="10 byte"):
        client.get("https://allowed.example/data")
