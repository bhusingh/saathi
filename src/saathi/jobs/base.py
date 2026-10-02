"""Reusable collection-job orchestration."""

from __future__ import annotations

from collections.abc import Iterable

from saathi.adapters.state_json import DedupeStore
from saathi.domain.formatting import canonical_url
from saathi.domain.models import Item, Sheet, SourceError
from saathi.domain.ports import Clock, Source


class CollectionJob:
    """Collect independent sources into a deduplicated data sheet."""

    def __init__(
        self,
        title: str,
        sources: Iterable[Source],
        clock: Clock,
        dedupe: DedupeStore | None = None,
        notes: tuple[str, ...] = (),
    ) -> None:
        self._title = title
        self._sources = tuple(sources)
        self._clock = clock
        self._dedupe = dedupe
        self._notes = notes

    def run(self) -> Sheet:
        """Run every source, isolating failures at the source boundary."""

        sections: list[tuple[str, tuple[Item, ...]]] = []
        errors: list[SourceError] = []
        for source in self._sources:
            try:
                items = self._fresh(source.collect())
            except Exception as exc:  # collectors must degrade independently
                errors.append(SourceError(source.name, type(exc).__name__))
                continue
            if items:
                sections.append((source.name, tuple(items)))
        if self._dedupe is not None:
            self._dedupe.save()
        return Sheet(
            title=self._title,
            generated_at=self._clock.now(),
            sections=tuple(sections),
            errors=tuple(errors),
            notes=self._notes,
        )

    def _fresh(self, items: list[Item]) -> list[Item]:
        if self._dedupe is None:
            return items
        return [
            item
            for item in items
            if self._dedupe.is_new(item.dedupe_key or canonical_url(item.url))
        ]
