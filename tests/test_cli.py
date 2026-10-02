import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from saathi.adapters.state_json import DeferredStateStore, JsonStateStore
from saathi.cli import _write_collection_result, valid_ticker
from saathi.domain.models import Item, Sheet, SourceError


@pytest.mark.parametrize("value", ["AAPL", "BRK-B", "^VIX", "BTC-USD"])
def test_valid_tickers(value: str) -> None:
    assert valid_ticker(value) == value


@pytest.mark.parametrize("value", ["", "TOO-LONG-SYMBOL", "AAPL;rm", "space here"])
def test_invalid_tickers(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        valid_ticker(value)


def test_empty_collection_is_silent_and_errors_go_to_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = DeferredStateStore(JsonStateStore(tmp_path))
    state.save("pending", {"saved": True})
    sheet = Sheet(
        "empty",
        datetime(2026, 1, 1, tzinfo=UTC),
        errors=(SourceError("feed", "TimeoutError"),),
    )
    _write_collection_result(sheet, "UTC", state)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "source unavailable: feed - TimeoutError" in captured.err
    assert JsonStateStore(tmp_path).load("pending") == {"saved": True}


def test_collection_state_is_not_committed_when_stdout_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenStdout:
        def write(self, value: str) -> int:
            raise BrokenPipeError

        def flush(self) -> None:
            pass

    state = DeferredStateStore(JsonStateStore(tmp_path))
    state.save("pending", {"saved": True})
    sheet = Sheet(
        "report",
        datetime(2026, 1, 1, tzinfo=UTC),
        sections=(("source", (Item("title", "https://example.com", "source"),)),),
    )
    monkeypatch.setattr(sys, "stdout", BrokenStdout())
    with pytest.raises(BrokenPipeError):
        _write_collection_result(sheet, "UTC", state)
    assert JsonStateStore(tmp_path).load("pending") == {}
