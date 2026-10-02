from datetime import UTC, datetime

from saathi.domain.formatting import canonical_url, clean_text, format_item, format_sheet
from saathi.domain.models import Item, Sheet, SourceError


def test_canonical_url_removes_tracking_and_fragment() -> None:
    assert (
        canonical_url("HTTPS://Example.COM/path/?b=2&utm_source=x&a=1#part")
        == "https://example.com/path?b=2&a=1"
    )


def test_clean_text_removes_markup_and_limits() -> None:
    assert clean_text("<b>Hello</b>  &amp; world", 12) == "Hello & worl"


def test_format_item_is_citation_ready() -> None:
    item = Item(
        "Title",
        "https://example.com/story",
        "Example",
        datetime(2026, 1, 2, 12, tzinfo=UTC),
        "Summary",
    )
    output = format_item(item)
    assert "[Example] Title" in output
    assert "<https://example.com/story>" in output
    assert "Summary" in output


def test_sheet_includes_isolated_errors() -> None:
    sheet = Sheet(
        "Test",
        datetime(2026, 1, 1, tzinfo=UTC),
        errors=(SourceError("broken", "TimeoutError"),),
    )
    assert "(source unavailable: broken - TimeoutError)" in format_sheet(sheet)
