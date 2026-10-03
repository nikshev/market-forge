"""Telegram authentication, as configuration (REQ-WP-080, Principle X)."""

from __future__ import annotations

import pytest

from channelflow.settings import MissingConfiguration, settings_from_env

BASE = {"CHANNELFLOW_CATALOG_URI": "sqlite:///x.db", "CHANNELFLOW_WAREHOUSE": "/tmp/w"}
TOKEN = "123456:TEST-TOKEN-NOT-A-SECRET"


@pytest.mark.trace("REQ-WP-080")
def test_authentication_is_off_unless_it_is_asked_for() -> None:
    settings = settings_from_env(BASE)

    assert settings.telegram_auth == "off"
    assert settings.telegram_max_age_seconds == 86_400


@pytest.mark.trace("REQ-WP-080")
def test_required_with_a_token_is_accepted_and_the_age_is_read() -> None:
    settings = settings_from_env(
        {
            **BASE,
            "CHANNELFLOW_TELEGRAM_AUTH": "required",
            "TELEGRAM_BOT_TOKEN": TOKEN,
            "CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS": "600",
        }
    )

    assert settings.telegram_auth == "required" and settings.telegram_max_age_seconds == 600


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("token", [None, "", "   "])
def test_required_without_a_token_stops_the_service_and_names_the_variable(
    token: str | None,
) -> None:
    """Refuse to start rather than serve open: a deployment that asked for authentication and has
    none must not look the same as one that has it."""
    env = {**BASE, "CHANNELFLOW_TELEGRAM_AUTH": "required"}
    if token is not None:
        env["TELEGRAM_BOT_TOKEN"] = token

    with pytest.raises(MissingConfiguration, match="TELEGRAM_BOT_TOKEN"):
        settings_from_env(env)


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("value", ["on", "true", "REQUIRED", "1", "optional"])
def test_any_other_mode_is_refused_not_guessed(value: str) -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_TELEGRAM_AUTH"):
        settings_from_env({**BASE, "CHANNELFLOW_TELEGRAM_AUTH": value, "TELEGRAM_BOT_TOKEN": TOKEN})


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("value", ["0", "-5", "soon", "1.5"])
def test_a_maximum_age_that_is_not_a_positive_whole_number_is_refused(value: str) -> None:
    with pytest.raises(MissingConfiguration, match="CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS"):
        settings_from_env(
            {
                **BASE,
                "CHANNELFLOW_TELEGRAM_AUTH": "required",
                "TELEGRAM_BOT_TOKEN": TOKEN,
                "CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS": value,
            }
        )


@pytest.mark.trace("REQ-WP-080")
def test_the_token_never_appears_in_the_settings_text() -> None:
    """`repr` and `str` are the one masked text; whichever were unmasked would end up in a log."""
    settings = settings_from_env(
        {**BASE, "CHANNELFLOW_TELEGRAM_AUTH": "required", "TELEGRAM_BOT_TOKEN": TOKEN}
    )

    assert TOKEN not in repr(settings) and TOKEN not in str(settings)
