"""Market brief computation using injected Yahoo tickers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from saathi.adapters.yahoo import YahooMarketData
from saathi.markets.options import (
    black_scholes_greeks,
    expected_move,
    options_market_hours,
    pick_expiry,
)


def relative_strength_index(closes: Any, periods: int = 14) -> float:
    """Calculate a simple rolling RSI from a pandas-like series."""

    difference = closes.diff().dropna()
    gain = difference.clip(lower=0).rolling(periods).mean().iloc[-1]
    loss = (-difference.clip(upper=0)).rolling(periods).mean().iloc[-1]
    return 100.0 if not loss else float(100 - 100 / (1 + gain / loss))


def stock_summary(symbol: str, ticker: Any) -> tuple[str, float | None]:
    """Build a deterministic technical summary for one symbol."""

    history = ticker.history(period="1y", auto_adjust=False)
    if history.empty or len(history) < 25:
        return f"{symbol}: no price data", None
    closes = history["Close"]
    latest = float(closes.iloc[-1])
    previous = float(closes.iloc[-2])
    five_day = float(closes.iloc[-6])
    volume = float(history["Volume"].iloc[-1])
    average = float(history["Volume"].iloc[-21:-1].mean())
    high = float(history["High"].max())
    low = float(history["Low"].min())
    fields = [
        f"{symbol}: ${latest:.2f} ({(latest / previous - 1) * 100:+.2f}% d/d, "
        f"{(latest / five_day - 1) * 100:+.1f}% 5d)",
        f"vol {volume / average:.1f}x 20d avg" if average else "vol n/a",
        f"52w range ${low:.2f}-${high:.2f}",
        f"RSI14 {relative_strength_index(closes):.0f}",
    ]
    return " | ".join(fields), latest


def options_summary(ticker: Any, spot: float, now: datetime) -> list[str]:
    """Compute current-expiry options context only inside the trusted time window."""

    if not options_market_hours(now):
        return []
    expiries = list(ticker.options)
    selected = pick_expiry(expiries, now.astimezone(ZoneInfo("America/New_York")).date())
    if selected is None:
        return ["  options: none listed"]
    expiry, days = selected
    chain = ticker.option_chain(expiry)
    calls, puts = chain.calls, chain.puts
    near = [
        frame.iloc[(frame["strike"] - spot).abs().argsort()[:3]]["impliedVolatility"]
        for frame in (calls, puts)
    ]
    values = [float(value) for column in near for value in column if 0.05 < value < 5]
    volatility = sum(values) / len(values) if values else None
    call_volume = float(calls["volume"].fillna(0).sum())
    put_volume = float(puts["volume"].fillna(0).sum())
    years = max(days, 1) / 365
    line = f"  options exp {expiry} ({days}d):"
    if volatility is not None:
        move = expected_move(spot, volatility, years)
        line += f" ATM IV {volatility * 100:.0f}%, expected move ±${move:.2f}"
    else:
        line += " ATM IV unavailable"
    if call_volume:
        line += f" | P/C volume {put_volume / call_volume:.2f}"
    lines = [line]
    if volatility is not None and not calls.empty:
        nearest = calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]
        strike = float(nearest["strike"].iloc[0])
        greeks = black_scholes_greeks(spot, strike, years, volatility)
        if greeks is not None:
            lines.append(
                f"  ATM {strike:g}C greeks: delta {greeks.delta:.2f}, "
                f"gamma {greeks.gamma:.3f}, theta ${greeks.theta:.3f}/day, "
                f"vega ${greeks.vega:.3f}/IV pt"
            )
    return lines


def market_brief(symbols: list[str], data: YahooMarketData, instant: datetime | None = None) -> str:
    """Generate a delayed-data sheet while isolating ticker failures."""

    now = instant or datetime.now(UTC)
    lines = [
        f"MARKET DATA SHEET - generated {now:%Y-%m-%d %H:%M UTC}",
        "Yahoo Finance is unofficial and may be delayed. Research only, not advice.",
    ]
    if not options_market_hours(now):
        lines.append(
            "Options IV/greeks/OI skipped outside 09:45-16:45 ET because Yahoo data is stale."
        )
    for symbol in symbols:
        try:
            ticker = data.ticker(symbol)
            summary, spot = stock_summary(symbol, ticker)
            lines.append(summary)
            if spot is not None:
                lines.extend(options_summary(ticker, spot, now))
        except Exception as exc:
            lines.append(f"(source unavailable: Yahoo {symbol} - {type(exc).__name__})")
    return "\n".join(lines)
