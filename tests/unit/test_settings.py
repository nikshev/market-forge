"""Configuration that cannot render its own credentials (REQ-WP-072).

PRD §34: *"redact secrets from logs"*. Measured before this existed, `Settings`
was a frozen dataclass whose generated `repr` printed the Postgres password
inside `catalog_uri` **and** `storage['s3.secret-access-key']` in full. That is
not a logging problem waiting for logging: the object was built to leak, and a
log line, an f-string, an assertion message or a traceback rendering locals
would each have been the delivery.

So the rule is on the type. What stays visible is as much a part of it as what
goes: a mask that hid everything would make the object useless to read, and
whoever needed the host would render the fields one at a time -- the same leak
by a longer road.
"""

from __future__ import annotations

import pytest

from channelflow.settings import (
    InvalidRateLimit,
    RateLimit,
    Settings,
    WildcardOrigin,
    mask_password,
    settings_from_env,
)

SECRET = "sup3rs3cret"
S3_SECRET = "AKIA-SECRET-VALUE"

BASE = {
    "CHANNELFLOW_CATALOG_URI": f"postgresql+psycopg://cf:{SECRET}@db:5432/cf",
    "CHANNELFLOW_WAREHOUSE": "s3://bucket/warehouse",
    "CHANNELFLOW_S3_ENDPOINT": "http://minio:9000",
    "CHANNELFLOW_S3_ACCESS_KEY_ID": "keyid",
    "CHANNELFLOW_S3_SECRET_ACCESS_KEY": S3_SECRET,
}


def _settings(**overrides: str) -> Settings:
    return settings_from_env({**BASE, **overrides})


# --- T006-T010: a credential cannot be rendered -----------------------------


@pytest.mark.trace("REQ-WP-072")
def test_the_password_and_the_s3_secret_are_masked() -> None:
    rendered = repr(_settings())
    assert SECRET not in rendered
    assert S3_SECRET not in rendered
    assert "***" in rendered


@pytest.mark.trace("REQ-WP-072")
def test_what_survives_the_mask_is_what_makes_it_readable() -> None:
    """A mask that hid everything would be a leak by a longer road."""
    rendered = repr(_settings())
    assert "postgresql+psycopg" in rendered
    assert "cf@" in rendered or "cf:***" in rendered
    assert "db" in rendered
    assert "5432" in rendered
    assert "keyid" in rendered, "an access key id is an identifier, not a secret"
    assert "s3://bucket/warehouse" in rendered


@pytest.mark.trace("REQ-WP-072")
def test_there_is_one_masked_spelling_not_a_masked_and_an_unmasked_one() -> None:
    settings = _settings()
    assert str(settings) == repr(settings)


@pytest.mark.trace("REQ-WP-072")
def test_string_formatting_is_masked_too() -> None:
    settings = _settings()
    assert SECRET not in f"{settings}"
    assert SECRET not in "{}".format(settings)  # noqa: UP032
    assert SECRET not in f"{settings!r}"
    assert SECRET not in f"{settings!s}"


@pytest.mark.trace("REQ-WP-072")
def test_a_uri_with_no_password_is_unchanged() -> None:
    settings = _settings(CHANNELFLOW_CATALOG_URI="postgresql+psycopg://db:5432/cf")
    assert "postgresql+psycopg://db:5432/cf" in repr(settings)
    assert "***" not in repr(settings).split("storage=")[0]


@pytest.mark.trace("REQ-WP-072")
@pytest.mark.parametrize(
    "password",
    ["p@ssword", "a:b:c", "with@at:and:colons", "]weird[", "p@ss:w@rd", "::@@::"],
)
def test_a_password_full_of_punctuation_is_still_fully_masked(password: str) -> None:
    """Splitting the URI on the wrong `@` or `:` leaves most of the secret behind.

    Asserted as an exact string rather than as "the password is absent". Both
    off-by-one splits leave the whole password *missing* while leaving most of it
    *present*: `p@ssword` becomes `cf:***@ssword@db`, and `a:b:c` becomes
    `cf:a:b:***@db`. A containment check passes on both, which is how a mask that
    redacts a single character can look correct.
    """
    uri = f"postgresql+psycopg://cf:{password}@db:5432/cf"
    assert mask_password(uri) == "postgresql+psycopg://cf:***@db:5432/cf"
    assert password not in repr(_settings(CHANNELFLOW_CATALOG_URI=uri))


@pytest.mark.trace("REQ-WP-072")
def test_a_user_with_no_password_keeps_its_at_sign() -> None:
    assert (
        mask_password("postgresql+psycopg://cf@db:5432/cf") == "postgresql+psycopg://cf@db:5432/cf"
    )


@pytest.mark.trace("REQ-WP-072")
def test_something_that_is_not_a_uri_is_returned_unchanged() -> None:
    assert mask_password("sqlite:///local.db") == "sqlite:///local.db"
    assert mask_password("not a uri at all") == "not a uri at all"


@pytest.mark.trace("REQ-WP-072")
def test_the_values_themselves_are_untouched() -> None:
    """Masking is a rendering rule. The process still needs the real credential."""
    settings = _settings()
    assert settings.catalog_uri == BASE["CHANNELFLOW_CATALOG_URI"]
    assert settings.storage["s3.secret-access-key"] == S3_SECRET


# --- T002-T005: the new configuration ---------------------------------------


@pytest.mark.trace("REQ-WP-072")
@pytest.mark.parametrize(("requests", "window"), [(0, 60.0), (-1, 60.0), (5, 0.0), (5, -1.0)])
def test_a_limit_that_forbids_everything_is_not_a_limit(requests: int, window: float) -> None:
    with pytest.raises(InvalidRateLimit):
        RateLimit(requests=requests, window_seconds=window)


@pytest.mark.trace("REQ-WP-072")
def test_a_sub_second_window_is_allowed() -> None:
    assert RateLimit(requests=1, window_seconds=0.5).window_seconds == 0.5


@pytest.mark.trace("REQ-WP-072")
def test_unlimited_is_a_state_that_must_be_chosen() -> None:
    """Absent means no limiter -- not a parse failure, and not a default number."""
    assert _settings().rate_limit is None


@pytest.mark.trace("REQ-WP-072")
def test_a_configured_limit_is_read_with_its_window() -> None:
    settings = _settings(CHANNELFLOW_RATE_LIMIT="120", CHANNELFLOW_RATE_WINDOW_SECONDS="30")
    assert settings.rate_limit == RateLimit(requests=120, window_seconds=30.0)


@pytest.mark.trace("REQ-WP-072")
def test_a_limit_without_a_window_gets_the_documented_default() -> None:
    assert _settings(CHANNELFLOW_RATE_LIMIT="10").rate_limit == RateLimit(
        requests=10, window_seconds=60.0
    )


@pytest.mark.trace("REQ-WP-072")
def test_no_origins_means_no_allowance_at_all() -> None:
    assert _settings().allowed_origins == ()


@pytest.mark.trace("REQ-WP-072")
def test_origins_are_read_as_a_list() -> None:
    settings = _settings(CHANNELFLOW_CORS_ORIGINS="https://a.example, https://b.example")
    assert settings.allowed_origins == ("https://a.example", "https://b.example")


@pytest.mark.trace("REQ-WP-072")
@pytest.mark.parametrize("origins", ["*", "https://a.example, *", " * ", "*,https://a.example"])
def test_a_wildcard_is_refused_where_configuration_is_read(origins: str) -> None:
    """A wildcard among others is still a wildcard."""
    with pytest.raises(WildcardOrigin):
        _settings(CHANNELFLOW_CORS_ORIGINS=origins)


# --- the offered set (REQ-WP-074) -------------------------------------------


@pytest.mark.trace("REQ-WP-074")
def test_timeframes_unset_is_an_empty_configuration() -> None:
    """Not an error: a deployment that resamples nothing still has its source."""
    assert _settings().timeframes == ()


@pytest.mark.trace("REQ-WP-074")
def test_timeframes_are_read_through_the_shared_parser() -> None:
    from channelflow.timeframes import TIMEFRAMES

    settings = _settings(CHANNELFLOW_TIMEFRAMES="1h,5m")
    assert settings.timeframes == (TIMEFRAMES["5m"], TIMEFRAMES["1h"])


@pytest.mark.trace("REQ-WP-074")
def test_an_unknown_timeframe_refuses_at_startup() -> None:
    from channelflow.timeframes import UnknownTimeframe

    with pytest.raises(UnknownTimeframe):
        _settings(CHANNELFLOW_TIMEFRAMES="7m")


@pytest.mark.trace("REQ-WP-074")
def test_a_calendar_period_refuses_at_startup() -> None:
    from channelflow.timeframes import CalendarPeriod

    with pytest.raises(CalendarPeriod):
        _settings(CHANNELFLOW_TIMEFRAMES="1M")
