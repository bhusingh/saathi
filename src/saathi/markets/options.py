"""Pure options math and market-hours policy."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class Greeks:
    """Black-Scholes sensitivities for one option."""

    delta: float
    gamma: float
    theta: float
    vega: float


def normal_cdf(value: float) -> float:
    """Standard normal cumulative distribution."""

    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def normal_pdf(value: float) -> float:
    """Standard normal probability density."""

    return math.exp(-(value**2) / 2) / math.sqrt(2 * math.pi)


def black_scholes_greeks(
    spot: float,
    strike: float,
    years: float,
    volatility: float,
    *,
    call: bool = True,
    risk_free: float = 0.04,
) -> Greeks | None:
    """Calculate Black-Scholes Greeks, returning none for invalid inputs."""

    if min(spot, strike, years, volatility) <= 0:
        return None
    root_time = math.sqrt(years)
    d1 = (math.log(spot / strike) + (risk_free + volatility**2 / 2) * years) / (
        volatility * root_time
    )
    d2 = d1 - volatility * root_time
    delta = normal_cdf(d1) if call else normal_cdf(d1) - 1
    gamma = normal_pdf(d1) / (spot * volatility * root_time)
    vega = spot * normal_pdf(d1) * root_time / 100
    carry = risk_free * strike * math.exp(-risk_free * years)
    decay = -spot * normal_pdf(d1) * volatility / (2 * root_time)
    theta = (
        (decay - carry * normal_cdf(d2)) / 365 if call else (decay + carry * normal_cdf(-d2)) / 365
    )
    return Greeks(delta, gamma, theta, vega)


def expected_move(spot: float, volatility: float, years: float) -> float:
    """Calculate the one-standard-deviation option-implied move."""

    return spot * volatility * math.sqrt(years)


def options_market_hours(instant: datetime) -> bool:
    """Gate Yahoo IV/OI analytics to 09:45-16:45 US/Eastern weekdays."""

    eastern = instant.astimezone(ZoneInfo("America/New_York"))
    minute = eastern.hour * 60 + eastern.minute
    return eastern.weekday() < 5 and 9 * 60 + 45 <= minute <= 16 * 60 + 45


def pick_expiry(
    expiries: list[str], today: date, low: int = 14, high: int = 45
) -> tuple[str, int] | None:
    """Pick the first expiry in a preferred window, then the nearest future date."""

    dated = sorted((expiry, (date.fromisoformat(expiry) - today).days) for expiry in expiries)
    preferred = [row for row in dated if low <= row[1] <= high]
    future = [row for row in dated if row[1] > 0]
    candidates = preferred or future
    return candidates[0] if candidates else None
