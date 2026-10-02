import json
from datetime import UTC, date, datetime
from pathlib import Path

from saathi.adapters.state_json import DedupeStore, JsonStateStore


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 5, tzinfo=UTC)

    def today(self) -> date:
        return self.now().date()


def test_json_state_round_trip_and_permissions(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path)
    store.save("test", {"a": 1})
    assert store.load("test") == {"a": 1}
    assert (tmp_path / "test.json").stat().st_mode & 0o077 == 0


def test_invalid_or_non_mapping_state_is_empty(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text(json.dumps([1, 2]))
    assert JsonStateStore(tmp_path).load("bad") == {}


def test_dedupe_persists_hashes(tmp_path: Path) -> None:
    first = DedupeStore(JsonStateStore(tmp_path), "news", FixedClock())
    assert first.is_new("https://example.com/a")
    assert not first.is_new("https://example.com/a")
    first.save()
    second = DedupeStore(JsonStateStore(tmp_path), "news", FixedClock())
    assert not second.is_new("https://example.com/a")


def test_invalid_namespace_is_rejected(tmp_path: Path) -> None:
    store = JsonStateStore(tmp_path)
    try:
        store.load("../escape")
    except ValueError as exc:
        assert "namespace" in str(exc)
    else:
        raise AssertionError("expected namespace validation")
