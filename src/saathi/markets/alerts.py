"""Threshold-based, daily-deduplicated market alerts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from saathi.domain.models import Alert, PriceChange


def market_hours(instant: datetime) -> bool:
    """Return true during the configured alert window on US weekdays."""

    eastern = instant.astimezone(ZoneInfo("America/New_York"))
    minute = eastern.hour * 60 + eastern.minute
    return eastern.weekday() < 5 and 9 * 60 + 30 <= minute <= 16 * 60 + 5


def market_date(instant: datetime) -> date:
    """Return the US/Eastern trading date for an instant."""

    return instant.astimezone(ZoneInfo("America/New_York")).date()


def threshold_bucket(percent: float, step: float) -> int:
    """Return a signed count of crossed percentage thresholds."""

    count = int(abs(percent) // step)
    return count if percent >= 0 else -count


def new_price_alert(change: PriceChange, step: float, state: dict[str, Any]) -> Alert | None:
    """Return an alert only when a symbol crosses a new daily bucket."""

    bucket = threshold_bucket(change.percent, step)
    previous = state.get(change.symbol, 0)
    previous_bucket = previous if isinstance(previous, int) else 0
    if bucket == 0 or abs(bucket) <= abs(previous_bucket):
        return None
    state[change.symbol] = bucket
    direction = "up" if change.percent > 0 else "down"
    message = (
        f"- **{change.symbol}** {direction} {change.percent:+.1f}% today (${change.price:.2f})"
    )
    return Alert(f"price:{change.symbol}:{bucket}", message)


def daily_state(state: dict[str, Any], today: date) -> dict[str, Any]:
    """Reset an alert state mapping when its UTC day changes."""

    return state if state.get("day") == today.isoformat() else {"day": today.isoformat()}


def new_vix_alerts(
    change: PriceChange, levels: list[float], jump_percent: float, state: dict[str, Any]
) -> list[Alert]:
    """Return newly crossed VIX level and daily-jump alerts."""

    alerts: list[Alert] = []
    level = max((value for value in levels if change.price >= value), default=0)
    old_level = state.get("vix_level", 0)
    previous = float(old_level) if isinstance(old_level, (int, float)) else 0
    if level > previous:
        state["vix_level"] = level
        alerts.append(
            Alert(f"vix:level:{level}", f"- **VIX at {change.price:.1f}** (above {level:g})")
        )
    if change.percent >= jump_percent and not state.get("vix_jump"):
        state["vix_jump"] = True
        alerts.append(
            Alert(
                "vix:jump",
                f"- **VIX jumped {change.percent:+.0f}%** today to {change.price:.1f}",
            )
        )
    return alerts


def new_circuit_alerts(
    change: PriceChange, levels: list[float], state: dict[str, Any]
) -> list[Alert]:
    """Return newly crossed S&P 500 downside circuit-breaker levels."""

    alerts: list[Alert] = []
    for level in sorted(levels, reverse=True):
        key = f"circuit:{level:g}"
        if change.percent <= level and not state.get(key):
            state[key] = True
            alerts.append(
                Alert(key, f"- **S&P 500 {change.percent:.1f}% - crossed {level:g}% level**")
            )
    return alerts
