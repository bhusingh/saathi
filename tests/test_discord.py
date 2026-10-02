import pytest

from saathi.adapters.discord_api import DiscordApiError, parse_allowed_users


def test_allowlist_drops_blank_entries() -> None:
    assert parse_allowed_users(" 123456789012345, ,123456789012346,") == {
        "123456789012345",
        "123456789012346",
    }


@pytest.mark.parametrize("value", ["", " , , "])
def test_allowlist_refuses_empty_values(value: str) -> None:
    with pytest.raises(DiscordApiError, match="at least one"):
        parse_allowed_users(value)


def test_allowlist_refuses_non_numeric_ids() -> None:
    with pytest.raises(DiscordApiError, match="invalid numeric"):
        parse_allowed_users("owner-name")
