from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from saathi.adapters.github import GitHubTrendingSource, star_delta
from saathi.adapters.state_json import JsonStateStore


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 2, 1, tzinfo=UTC)

    def today(self) -> date:
        return self.now().date()


class FakeHttp:
    def get(self, url: str, *, accept: str | None = None) -> bytes:
        return b""

    def get_json(self, url: str) -> Any:
        return {}


def test_star_delta_uses_latest_prior_snapshot() -> None:
    gain, days = star_delta({"2026-01-01": 10, "2026-01-03": 14}, "2026-01-05", 20)
    assert (gain, days) == (6, 2)


def test_star_delta_first_observation() -> None:
    assert star_delta({}, "2026-01-05", 20) == (None, None)


def test_snapshot_history_guards_invalid_shapes_and_prunes_stale_repos(tmp_path: Path) -> None:
    state = JsonStateStore(tmp_path)
    state.save(
        "github_snapshots",
        {
            "org/broken": ["not", "a", "mapping"],
            "org/old": {"2025-12-01": 1},
            "org/recent": {"2026-01-20": 2},
        },
    )
    source = GitHubTrendingSource(FakeHttp(), state, FixedClock(), [], rate_delay=0)
    source._rank(
        {
            "org/broken": {
                "stargazers_count": 5,
                "html_url": "https://github.com/org/broken",
            }
        }
    )
    snapshots = state.load("github_snapshots")
    assert "org/old" not in snapshots
    assert snapshots["org/recent"] == {"2026-01-20": 2}
    assert snapshots["org/broken"] == {"2026-02-01": 5}
