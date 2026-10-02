"""Optional Yahoo Finance market-data adapter."""

from __future__ import annotations

import importlib
from datetime import date, timedelta
from typing import Any, cast

from saathi.domain.models import PriceChange


class YahooMarketData:
    """Read delayed, unofficial market data through optional yfinance."""

    @staticmethod
    def _ticker(symbol: str) -> Any:
        try:
            module = importlib.import_module("yfinance")
        except ImportError as exc:
            message = "install the markets extra: pip install 'saathi-agent[markets]'"
            raise RuntimeError(message) from exc
        return module.Ticker(symbol)

    def change(self, symbol: str) -> PriceChange | None:
        """Return the latest close relative to the preceding close."""

        history = self._ticker(symbol).history(period="5d", interval="1d")
        if len(history) < 2:
            return None
        latest = float(history["Close"].iloc[-1])
        previous = float(history["Close"].iloc[-2])
        return PriceChange(symbol=symbol, price=latest, percent=(latest / previous - 1) * 100)

    def fundamentals(self, symbol: str) -> dict[str, Any]:
        """Return the provider's fundamentals mapping."""

        value = self._ticker(symbol).info or {}
        return cast(dict[str, Any], value) if isinstance(value, dict) else {}

    def ticker(self, symbol: str) -> Any:
        """Expose a ticker to higher-level market sheets."""

        return self._ticker(symbol)

    def economic_events(self, start: date, end: date) -> list[dict[str, Any]]:
        """Read US economic-calendar rows in daily pages to avoid provider caps."""

        module = importlib.import_module("yfinance")
        rows: list[dict[str, Any]] = []
        day = start
        while day <= end:
            calendar = module.Calendars(start=day, end=day + timedelta(days=1))
            frame = calendar.get_economic_events_calendar(limit=100)
            for name, raw in frame.iterrows():
                if str(raw.get("Region", "")).strip() != "US":
                    continue
                rows.append(
                    {
                        "name": str(name),
                        "when": raw.get("Event Time"),
                        "actual": raw.get("Actual"),
                        "expected": raw.get("Expected"),
                        "last": raw.get("Last"),
                    }
                )
            day += timedelta(days=1)
        return rows
