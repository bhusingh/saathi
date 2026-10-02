"""openFDA animal-product recall source."""

from __future__ import annotations

import re
from datetime import timedelta
from urllib.parse import quote

from saathi.domain.models import Item
from saathi.domain.ports import Clock, HttpClient

ANIMAL_TERMS = re.compile(
    r"\b(dogs?|cats?|canine|feline|puppy|kitten|pet food|pet treats?|animal food)\b", re.I
)


def is_animal_product(description: str) -> bool:
    """Reject false positives such as PET plastic packaging."""

    return ANIMAL_TERMS.search(description) is not None


class OpenFdaRecallSource:
    """Collect recent pet food and animal-drug enforcement reports."""

    name = "openFDA"

    def __init__(self, http: HttpClient, clock: Clock, lookback_days: int = 30) -> None:
        self._http = http
        self._clock = clock
        self._lookback_days = lookback_days

    def collect(self) -> list[Item]:
        """Fetch relevant recalls using defensive local filtering."""

        since = (self._clock.today() - timedelta(days=self._lookback_days)).strftime("%Y%m%d")
        query = (
            "(product_description:dog OR product_description:cat OR product_description:pet "
            f'OR product_description:"animal food") AND report_date:[{since} TO 29991231]'
        )
        url = (
            "https://api.fda.gov/food/enforcement.json?search="
            f"{quote(query)}&sort=report_date:desc&limit=20"
        )
        data = self._http.get_json(url)
        results = data.get("results", []) if isinstance(data, dict) else []
        items: list[Item] = []
        for raw in results if isinstance(results, list) else []:
            if not isinstance(raw, dict):
                continue
            description = str(raw.get("product_description", ""))
            if not is_animal_product(description):
                continue
            recall = str(raw.get("recall_number", "unknown"))
            summary = (
                f"{raw.get('classification', 'unclassified')}, {raw.get('status', 'unknown')}. "
                f"{description[:180]} Reason: {str(raw.get('reason_for_recall', ''))[:200]}"
            )
            items.append(
                Item(
                    title=f"{raw.get('recalling_firm', 'Unknown firm')} recall {recall}",
                    url="https://open.fda.gov/apis/food/enforcement/",
                    source=self.name,
                    dedupe_key=recall,
                    summary=summary,
                    metadata={"recall_number": recall},
                )
            )
        return items
