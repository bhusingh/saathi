from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from saathi.markets.options import (
    black_scholes_greeks,
    expected_move,
    options_market_hours,
    pick_expiry,
)


def test_black_scholes_known_at_the_money_values() -> None:
    greeks = black_scholes_greeks(100, 100, 1, 0.2, risk_free=0.05)
    assert greeks is not None
    assert greeks.delta == pytest.approx(0.6368, abs=0.001)
    assert greeks.gamma == pytest.approx(0.0188, abs=0.001)
    assert greeks.vega == pytest.approx(0.3752, abs=0.001)


def test_invalid_greeks_and_expected_move() -> None:
    assert black_scholes_greeks(0, 100, 1, 0.2) is None
    assert expected_move(100, 0.2, 0.25) == pytest.approx(10)


def test_options_market_hours_gating() -> None:
    zone = ZoneInfo("America/New_York")
    assert options_market_hours(datetime(2026, 1, 5, 10, 0, tzinfo=zone))
    assert not options_market_hours(datetime(2026, 1, 5, 9, 44, tzinfo=zone))
    assert not options_market_hours(datetime(2026, 1, 4, 12, 0, tzinfo=zone))


def test_pick_expiry_prefers_window() -> None:
    assert pick_expiry(["2026-01-08", "2026-01-20"], date(2026, 1, 1)) == (
        "2026-01-20",
        19,
    )
