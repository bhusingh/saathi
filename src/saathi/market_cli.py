"""Composition helpers for market-related CLI commands."""

from __future__ import annotations

import argparse
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from saathi.adapters.state_json import JsonStateStore
from saathi.adapters.yahoo import YahooMarketData
from saathi.domain.config import ConfigError, ConfigPaths, load_yaml, require_mapping
from saathi.markets.alerts import (
    daily_state,
    market_date,
    market_hours,
    new_circuit_alerts,
    new_price_alert,
    new_vix_alerts,
)
from saathi.markets.brief import market_brief
from saathi.markets.deep_dive import run_deep_dive
from saathi.markets.fundamentals import fundamentals_sheet
from saathi.markets.macro_calendar import classify, parse_fomc_dates

TICKER = re.compile(r"^[A-Z0-9.^=-]{1,12}$")


def valid_ticker(value: str) -> str:
    """Validate and normalize a market symbol before provider use."""

    symbol = value.upper()
    if not TICKER.fullmatch(symbol):
        raise argparse.ArgumentTypeError("ticker must match ^[A-Z0-9.^=-]{1,12}$")
    return symbol


def run_market(args: argparse.Namespace, paths: ConfigPaths, state_dir: Path) -> int:
    """Run one market subcommand."""

    watchlist = load_yaml(paths.named("watchlist"))
    data = YahooMarketData()
    if args.market_command == "brief":
        print(market_brief(_ticker_list(watchlist.get("tickers"), "tickers"), data))
    elif args.market_command == "fundamentals":
        _fundamentals(args.tickers, data)
    elif args.market_command == "alerts":
        _market_alerts(state_dir, watchlist, data)
    elif args.market_command == "macro":
        _macro_week(paths, state_dir)
    elif args.market_command == "deep-dive":
        print(run_deep_dive(args.ticker, args.date))
    return 0


def _fundamentals(symbols: list[str], data: YahooMarketData) -> None:
    print("FUNDAMENTALS - Yahoo Finance (unofficial). Research only, not advice.")
    for symbol in symbols:
        try:
            print(fundamentals_sheet(symbol, data.fundamentals(symbol)))
        except Exception as exc:
            print(f"(source unavailable: Yahoo {symbol} - {type(exc).__name__})")


def _ticker_list(value: object, context: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{context} must be a list of tickers")
    values = []
    for item in value:
        try:
            values.append(valid_ticker(item))
        except argparse.ArgumentTypeError as exc:
            raise ConfigError(f"invalid ticker in {context}: {item}") from exc
    return values


def _market_alerts(state_dir: Path, watchlist: dict[str, Any], data: YahooMarketData) -> None:
    now = datetime.now(UTC)
    if not market_hours(now):
        return
    state_store = JsonStateStore(state_dir)
    state = daily_state(state_store.load("market_alerts"), market_date(now))
    thresholds = require_mapping(watchlist.get("alert_thresholds"), "alert_thresholds")
    stock_step = float(thresholds.get("stock_percent", 5.0))
    index_step = float(thresholds.get("index_percent", 2.0))
    lines: list[str] = []
    symbols = [
        *[(symbol, stock_step) for symbol in _ticker_list(watchlist.get("tickers"), "tickers")],
        *[
            (symbol, index_step)
            for symbol in _ticker_list(watchlist.get("index_tickers"), "index_tickers")
        ],
    ]
    for symbol, step in symbols:
        try:
            change = data.change(symbol)
        except Exception:
            continue
        alert = new_price_alert(change, step, state) if change else None
        if alert:
            lines.append(alert.message)
    _append_volatility_alerts(lines, state, thresholds, data)
    state_store.save("market_alerts", state)
    if lines:
        print("**Market alert** (Yahoo Finance, delayed and unofficial)\n" + "\n".join(lines))


def _append_volatility_alerts(
    lines: list[str], state: dict[str, Any], thresholds: dict[str, Any], data: YahooMarketData
) -> None:
    try:
        vix = data.change("^VIX")
        levels = [float(value) for value in thresholds.get("vix_levels", [])]
        if vix:
            lines.extend(
                alert.message
                for alert in new_vix_alerts(
                    vix, levels, float(thresholds.get("vix_jump_percent", 20)), state
                )
            )
    except Exception:
        pass
    try:
        spx = data.change("^GSPC")
        breakers = [float(value) for value in thresholds.get("circuit_breakers", [])]
        if spx:
            lines.extend(alert.message for alert in new_circuit_alerts(spx, breakers, state))
    except Exception:
        pass


def _macro_week(paths: ConfigPaths, state_dir: Path) -> None:
    from saathi.operations import source_dependencies

    _, http, _ = source_dependencies(paths, state_dir)
    today = date.today()
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    print(f"MACRO CALENDAR - week of {today:%b %d}")
    found = False
    try:
        html = http.get(url).decode("utf-8", errors="replace")
        upcoming = [day for day in parse_fomc_dates(html, today.year) if today <= day]
        week = [day for day in upcoming if (day - today).days <= 7]
    except Exception as exc:
        week = []
        print(f"(source unavailable: Federal Reserve - {type(exc).__name__})")
    for day in week:
        print(f"- {day:%a %b %d}: FOMC decision; verify the current Fed schedule")
        found = True
    try:
        events = YahooMarketData().economic_events(today, today + date.resolution * 7)
        for event in events:
            impact = classify(str(event["name"]))
            if impact is not None:
                found = True
                print(
                    f"- {event['when']}: {impact.label} | forecast "
                    f"{event.get('expected', 'n/a')} | prior {event.get('last', 'n/a')}"
                )
    except Exception as exc:
        print(f"(source unavailable: Yahoo economic calendar - {type(exc).__name__})")
    if not found:
        print("- No high-impact US events found in the next seven days.")
    print(f"Source: {url}")
