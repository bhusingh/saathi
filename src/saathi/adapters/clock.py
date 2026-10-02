"""System clock adapter."""

from datetime import UTC, date, datetime


class SystemClock:
    """Return UTC-aware system time."""

    def now(self) -> datetime:
        """Return the current UTC instant."""

        return datetime.now(UTC)

    def today(self) -> date:
        """Return the current UTC date."""

        return self.now().date()
