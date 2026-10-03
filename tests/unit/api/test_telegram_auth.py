"""Telegram's launch signature, verified against answers the verifier did not write (REQ-WP-080).

`tests/vectors/telegram_init_data.json` holds nine launches and what must happen to each. Their
signatures were computed by `openssl` (`tests/vectors/make_vectors.sh`) -- a third implementation,
so
this verifier and the TypeScript dev signer are each checked against something neither wrote. A
verifier
tested only against its own signer proves nothing.

The boundary cases below are signed here with `hmac`, the same library the verifier uses; the
vectors
are what pin the algorithm itself.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from pathlib import Path
from urllib.parse import urlencode

import pytest

from channelflow.api.telegram_auth import LaunchData, LaunchRefused, verify_init_data

VECTORS = json.loads(
    (Path(__file__).resolve().parents[2] / "vectors" / "telegram_init_data.json").read_text()
)
TOKEN = VECTORS["bot_token"]
NOW = VECTORS["now"]
MAX_AGE = VECTORS["max_age_seconds"]


def _signed(fields: dict[str, str], token: str = TOKEN) -> str:
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    digest = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": digest})


def _launch(auth_date: int, **extra: str) -> str:
    return _signed({"query_id": "AAx", "auth_date": str(auth_date), **extra})


# --- the vectors --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_each_vector_gets_the_verdict_openssl_signed_it_for(case: dict[str, str]) -> None:
    if case["verdict"] == "accept":
        got = verify_init_data(case["init_data"], TOKEN, now=NOW, max_age_seconds=MAX_AGE)
        assert isinstance(got, LaunchData)
    else:
        with pytest.raises(LaunchRefused) as refused:
            verify_init_data(case["init_data"], TOKEN, now=NOW, max_age_seconds=MAX_AGE)
        assert refused.value.reason == case["reason"]


@pytest.mark.trace("REQ-WP-080")
def test_of_nine_launches_two_are_accepted_and_the_seven_refused_give_six_reasons() -> None:
    """SC-001. A changed field and a wrong token are one reason, `bad_signature`, on purpose:
    telling them apart would tell an attacker which half of a guess was right."""
    accepted, reasons = 0, []
    for case in VECTORS["cases"]:
        try:
            verify_init_data(case["init_data"], TOKEN, now=NOW, max_age_seconds=MAX_AGE)
            accepted += 1
        except LaunchRefused as refused:
            reasons.append(refused.reason)

    assert accepted == 2 and len(reasons) == 7
    assert len(set(reasons)) == 6


# --- the edges of age and skew -------------------------------------------------------------


@pytest.mark.trace("REQ-WP-080")
def test_a_launch_exactly_the_maximum_age_is_accepted_and_one_second_older_is_refused() -> None:
    verify_init_data(_launch(NOW - MAX_AGE), TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    with pytest.raises(LaunchRefused) as refused:
        verify_init_data(_launch(NOW - MAX_AGE - 1), TOKEN, now=NOW, max_age_seconds=MAX_AGE)
    assert refused.value.reason == "too_old"


@pytest.mark.trace("REQ-WP-080")
def test_a_launch_a_minute_ahead_is_accepted_and_sixty_one_seconds_ahead_is_refused() -> None:
    """Clock skew between Telegram's servers and this host: a minute either way."""
    verify_init_data(_launch(NOW + 60), TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    with pytest.raises(LaunchRefused) as refused:
        verify_init_data(_launch(NOW + 61), TOKEN, now=NOW, max_age_seconds=MAX_AGE)
    assert refused.value.reason == "from_the_future"


@pytest.mark.trace("REQ-WP-080")
def test_the_maximum_age_is_configuration_not_a_constant() -> None:
    launch = _launch(NOW - 500)

    verify_init_data(launch, TOKEN, now=NOW, max_age_seconds=501)
    with pytest.raises(LaunchRefused):
        verify_init_data(launch, TOKEN, now=NOW, max_age_seconds=499)


# --- identity is not needed, so it is not required or kept ------------------------------------


@pytest.mark.trace("REQ-WP-080")
def test_a_signed_launch_with_no_user_is_accepted_and_says_so() -> None:
    got = verify_init_data(_launch(NOW - 10), TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    assert got.has_user is False and got.auth_date == NOW - 10


@pytest.mark.trace("REQ-WP-080")
def test_a_malformed_user_field_is_still_a_signed_launch() -> None:
    """The user is never parsed. A launch Telegram signed is a launch Telegram signed, and parsing
    JSON the verifier has no use for would be one more way for a valid launch to be refused."""
    launch = _launch(NOW - 10, user="{not json")

    got = verify_init_data(launch, TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    assert got.has_user is True


@pytest.mark.trace("REQ-WP-080")
def test_the_result_carries_no_identity() -> None:
    got = verify_init_data(
        _launch(NOW - 10, user='{"id":7,"username":"tester"}'),
        TOKEN,
        now=NOW,
        max_age_seconds=MAX_AGE,
    )

    assert set(vars(got)) == {"auth_date", "has_user"}


# --- the token is never in anything that leaves the verifier ----------------------------------


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("case", [c for c in VECTORS["cases"] if c["verdict"] == "refuse"])
def test_no_refusal_names_the_token_or_the_hash(
    case: dict[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    provided_hash = dict(pair.split("=", 1) for pair in case["init_data"].split("&")).get(
        "hash", "-"
    )

    with pytest.raises(LaunchRefused) as refused:
        verify_init_data(case["init_data"], TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    text = f"{refused.value} {refused.value!r} {refused.value.reason}"
    assert TOKEN not in text and provided_hash not in text
    assert not [r for r in caplog.records if TOKEN in r.getMessage()]


@pytest.mark.trace("REQ-WP-080")
def test_an_empty_token_is_refused_not_used_as_a_key() -> None:
    """HMAC with an empty key works, and would accept anyone who signed with an empty one."""
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        verify_init_data(_launch(NOW - 10), "", now=NOW, max_age_seconds=MAX_AGE)


# --- found by the mutation sweep: three guards nothing tested -----------------------------------
#
# Written alongside the verifier, not before it, and recorded as such: the sweep
# (`telegram_auth.toml`) showed each of these could be removed with every test still green.


@pytest.mark.trace("REQ-WP-080")
def test_a_launch_that_names_a_field_twice_is_malformed_not_resolved_by_picking_one() -> None:
    """Two `auth_date`s: which one was signed is not a question to answer by taking the last."""
    valid = VECTORS["cases"][0]["init_data"]

    with pytest.raises(LaunchRefused) as refused:
        verify_init_data(valid + "&auth_date=1", TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    assert refused.value.reason == "malformed"


@pytest.mark.trace("REQ-WP-080")
def test_a_launch_of_absurd_size_is_refused_before_it_is_parsed() -> None:
    with pytest.raises(LaunchRefused) as refused:
        verify_init_data("a=" + "x" * 200_000, TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    assert refused.value.reason == "malformed"


@pytest.mark.trace("REQ-WP-080")
def test_a_hash_that_is_not_ascii_is_a_bad_signature_and_not_an_error() -> None:
    """`hmac.compare_digest` raises `TypeError` on a non-ASCII `str`; a refusal must not be a
    500."""
    launch = urlencode({"auth_date": str(NOW - 5), "hash": "é" * 64})

    with pytest.raises(LaunchRefused) as refused:
        verify_init_data(launch, TOKEN, now=NOW, max_age_seconds=MAX_AGE)

    assert refused.value.reason == "bad_signature"
