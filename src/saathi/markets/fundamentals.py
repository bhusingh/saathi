"""Deterministic fundamentals formatting."""

from __future__ import annotations

import math
from typing import Any

FIELDS = (
    ("Price", "currentPrice", "money"),
    ("Market cap", "marketCap", "big"),
    ("P/E (trailing)", "trailingPE", "multiple"),
    ("P/E (forward)", "forwardPE", "multiple"),
    ("PEG", "trailingPegRatio", "multiple"),
    ("Price/Sales", "priceToSalesTrailing12Months", "multiple"),
    ("Price/Book", "priceToBook", "multiple"),
    ("EV/EBITDA", "enterpriseToEbitda", "multiple"),
    ("EPS (ttm)", "trailingEps", "money"),
    ("EPS (forward)", "forwardEps", "money"),
    ("Revenue (ttm)", "totalRevenue", "big"),
    ("Revenue growth (yoy)", "revenueGrowth", "percent"),
    ("Earnings growth (yoy)", "earningsGrowth", "percent"),
    ("Gross margin", "grossMargins", "percent"),
    ("Operating margin", "operatingMargins", "percent"),
    ("Net margin", "profitMargins", "percent"),
    ("Return on equity", "returnOnEquity", "percent"),
    ("Free cash flow", "freeCashflow", "big"),
    ("Total cash", "totalCash", "big"),
    ("Total debt", "totalDebt", "big"),
    ("Debt/Equity", "debtToEquity", "number"),
    ("Dividend yield", "dividendYield", "percent_points"),
    ("Short % of float", "shortPercentOfFloat", "percent"),
    ("Analyst target (mean)", "targetMeanPrice", "money"),
    ("Analyst rating", "recommendationKey", "text"),
)


def format_value(value: object, kind: str) -> str:
    """Format an upstream fundamental without inventing unavailable values."""

    if value is None or value == "":
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    if kind == "text":
        return str(value)
    if not isinstance(value, (int, float)):
        return "n/a"
    if kind == "money":
        return f"${value:,.2f}"
    if kind == "big":
        return _format_big(float(value))
    if kind == "multiple":
        return f"{value:,.1f}x"
    if kind == "percent":
        return f"{value * 100:,.1f}%"
    if kind == "percent_points":
        return f"{value:,.2f}%"
    return f"{value:,.1f}"


def _format_big(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    for unit, divisor in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if absolute >= divisor:
            return f"{sign}${absolute / divisor:,.2f}{unit}"
    return f"{sign}${absolute:,.0f}"


def fundamentals_sheet(symbol: str, info: dict[str, Any]) -> str:
    """Render one ticker's fundamentals from provider data."""

    name = info.get("longName", "")
    sector = info.get("sector", "n/a")
    industry = info.get("industry", "n/a")
    lines = [f"## {symbol} - {name} ({sector} / {industry})"]
    lines.extend(f"  {label}: {format_value(info.get(key), kind)}" for label, key, kind in FIELDS)
    return "\n".join(lines)
