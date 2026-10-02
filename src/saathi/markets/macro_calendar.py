"""High-impact macro event classification and Fed calendar parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

HIGH_IMPACT: tuple[tuple[str, str, float | None, str], ...] = (
    (r"^Non-Farm Payrolls$", "Jobs report (NFP)", 75, "k"),
    (r"^Unemployment Rate$", "Unemployment rate", 0.2, "%"),
    (r"^CPI MM, SA$", "CPI m/m", 0.1, "%"),
    (r"^Core CPI MM, SA$", "Core CPI m/m", 0.1, "%"),
    (r"^CPI YY, NSA$", "CPI y/y", 0.2, "%"),
    (r"^Core PCE Price Index MM", "Core PCE m/m", 0.1, "%"),
    (r"^GDP", "GDP", 0.5, "%"),
    (r"^Retail Sales MM$", "Retail sales m/m", 0.4, "%"),
    (r"^PPI Final Demand MM$", "PPI m/m", 0.2, "%"),
    (r"^ISM Manufacturing PMI$", "ISM manufacturing", 1.5, ""),
    (r"^ISM N-Mfg PMI$", "ISM services", 1.5, ""),
    (r"FOMC|Fed Funds|Rate Decision", "Fed rate decision", 0.0, "%"),
    (r"Powell|Fed Chair", "Fed chair speaks", None, ""),
)


@dataclass(frozen=True, slots=True)
class Impact:
    """Classification policy for a macro event."""

    label: str
    surprise_threshold: float | None
    unit: str


def classify(name: str) -> Impact | None:
    """Return high-impact metadata for a provider event name."""

    for pattern, label, threshold, unit in HIGH_IMPACT:
        if re.search(pattern, name, re.I):
            return Impact(label, threshold, unit)
    return None


def parse_fomc_dates(html: str, year: int) -> list[date]:
    """Parse meeting decision dates from the Federal Reserve calendar HTML."""

    match = re.search(rf"{year} FOMC Meetings(.*?)(?:{year - 1} FOMC Meetings|$)", html, re.S)
    if match is None:
        return []
    meetings = re.findall(
        r"fomc-meeting__month[^>]*>\s*<strong>(\w+)</strong>.*?"
        r"fomc-meeting__date[^>]*>\s*([\d-]+)",
        match.group(1),
        re.S,
    )
    dates: list[date] = []
    for month, days in meetings:
        try:
            value = f"{month} {days.split('-')[-1]} {year}"
            dates.append(datetime.strptime(value, "%B %d %Y").date())
        except ValueError:
            continue
    return dates


def surprise(actual: float, reference: float, impact: Impact) -> tuple[float, bool]:
    """Compute provider-unit surprise and whether it crosses the configured threshold."""

    delta = actual - reference
    threshold = impact.surprise_threshold
    return delta, threshold is not None and abs(delta) >= max(threshold, 1e-9)
