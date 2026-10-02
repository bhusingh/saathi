"""Read recent successful Hermes cron output for roll-up jobs."""

from __future__ import annotations

import json
import time
from pathlib import Path

from saathi.domain.models import Item


class HermesOutputsSource:
    """Expose latest named job outputs as normalized local items."""

    def __init__(
        self,
        name: str,
        hermes_home: Path,
        job_names: list[str],
        *,
        max_age_hours: int = 24,
        characters: int = 2500,
    ) -> None:
        self.name = name
        self._home = hermes_home
        self._names = job_names
        self._max_age = max_age_hours * 3600
        self._characters = characters

    def collect(self) -> list[Item]:
        """Read bounded latest outputs without failing on absent jobs."""

        ids = self._job_ids()
        items: list[Item] = []
        for name in self._names:
            latest = self._latest(ids.get(name))
            summary = "(no recent output)" if latest is None else self._body(latest)
            items.append(
                Item(
                    title=f"{name} (latest output)",
                    url=f"local://hermes-output/{name.replace(' ', '-').lower()}",
                    source=self.name,
                    summary=summary,
                    metadata={"summary_limit": self._characters},
                )
            )
        return items

    def _job_ids(self) -> dict[str, str]:
        try:
            raw = json.loads((self._home / "cron/jobs.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        jobs = raw.get("jobs", []) if isinstance(raw, dict) else []
        rows = jobs.values() if isinstance(jobs, dict) else jobs
        return {
            str(row.get("name")): str(row.get("id"))
            for row in rows
            if isinstance(row, dict) and row.get("name") and row.get("id")
        }

    def _latest(self, job_id: str | None) -> Path | None:
        if job_id is None:
            return None
        directory = self._home / "cron/output" / job_id
        files = sorted(directory.glob("*.md"), key=lambda path: path.stat().st_mtime)
        if not files or time.time() - files[-1].stat().st_mtime > self._max_age:
            return None
        return files[-1]

    def _body(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "## Response" in text:
            text = text.split("## Response", 1)[1]
        return text.strip()[: self._characters]
