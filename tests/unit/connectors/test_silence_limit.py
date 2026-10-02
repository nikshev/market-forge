"""Which silence a session tolerates (REQ-WP-078).

# @trace: REQ-WP-078
"""

from __future__ import annotations

import pytest

from channelflow.connectors.session import (
    HYPERCORE,
    OKX,
    SECOND_NS,
    Keepalive,
    VenuePolicy,
    silence_limit_ns,
)


@pytest.mark.trace("REQ-WP-078")
def test_an_explicit_limit_wins() -> None:
    assert silence_limit_ns(OKX) == OKX.max_silence_ns == 60 * SECOND_NS


@pytest.mark.trace("REQ-WP-078")
def test_a_venue_that_gives_up_silently_falls_back_to_its_idle_timeout() -> None:
    """HyperCore has no `max_silence_ns` and does not announce its closes. It must still
    reconnect at its idle timeout, which is what the session did before, and which the
    fallback exists to keep."""
    assert HYPERCORE.max_silence_ns is None and HYPERCORE.announces_close is False

    assert silence_limit_ns(HYPERCORE) == HYPERCORE.idle_timeout_ns


@pytest.mark.trace("REQ-WP-078")
def test_a_venue_that_announces_close_and_names_no_limit_has_none() -> None:
    policy = VenuePolicy(
        venue="v",
        keepalive=Keepalive.SERVER_INITIATED,
        idle_timeout_ns=30 * SECOND_NS,
        announces_close=True,
    )

    assert silence_limit_ns(policy) is None
