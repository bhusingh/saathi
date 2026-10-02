from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from saathi.domain.models import PriceChange
from saathi.markets.alerts import (
    daily_state,
    market_date,
    market_hours,
    new_circuit_alerts,
    new_price_alert,
    new_vix_alerts,
    threshold_bucket,
)


def test_threshold_bucket_is_signed() -> None:
    assert threshold_bucket(4.9, 5) == 0
    assert threshold_bucket(10.1, 5) == 2
    assert threshold_bucket(-10.1, 5) == -2


def test_alert_only_on_new_daily_bucket() -> None:
    state: dict[str, object] = {"day": "2026-01-01"}
    change = PriceChange("TEST", 42.0, 5.2)
    assert new_price_alert(change, 5, state) is not None
    assert new_price_alert(change, 5, state) is None
    assert new_price_alert(PriceChange("TEST", 40, 10.1), 5, state) is not None


def test_daily_state_and_market_window() -> None:
    assert daily_state({"day": "old", "TEST": 1}, date(2026, 1, 2)) == {"day": "2026-01-02"}
    eastern = ZoneInfo("America/New_York")
    assert market_hours(datetime(2026, 1, 5, 9, 30, tzinfo=eastern))
    assert not market_hours(datetime(2026, 1, 5, 9, 29, tzinfo=eastern))
    assert market_hours(datetime(2026, 1, 5, 16, 5, tzinfo=eastern))
    assert not market_hours(datetime(2026, 1, 5, 16, 6, tzinfo=eastern))


def test_market_date_uses_eastern_not_utc() -> None:
    instant = datetime(2026, 1, 2, 2, tzinfo=UTC)
    assert market_date(instant) == date(2026, 1, 1)


def test_vix_and_circuit_alerts_dedupe() -> None:
    state: dict[str, object] = {}
    vix = PriceChange("^VIX", 31, 22)
    assert len(new_vix_alerts(vix, [30, 40], 20, state)) == 2
    assert new_vix_alerts(vix, [30, 40], 20, state) == []
    spx = PriceChange("^GSPC", 5000, -13.2)
    assert len(new_circuit_alerts(spx, [-7, -13, -20], state)) == 2
