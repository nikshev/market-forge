"""What a venue policy refuses to be (REQ-WP-078).

# @trace: REQ-WP-078
"""

from __future__ import annotations

import pytest

from channelflow.connectors.session import SECOND_NS, Keepalive, VenuePolicy


def _policy(**overrides: object) -> VenuePolicy:
    fields: dict[str, object] = {
        "venue": "v",
        "keepalive": Keepalive.CLIENT_INITIATED,
        "idle_timeout_ns": 30 * SECOND_NS,
        "client_ping_interval_ns": 15 * SECOND_NS,
        "ping_payload": "ping",
    }
    fields.update(overrides)
    return VenuePolicy(**fields)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("silence", [0, -1])
def test_a_silence_limit_must_be_positive(silence: int) -> None:
    with pytest.raises(ValueError, match="max_silence"):
        _policy(max_silence_ns=silence)


@pytest.mark.trace("REQ-WP-078")
def test_a_silence_limit_shorter_than_the_keepalive_is_refused() -> None:
    """It would reconnect a healthy quiet connection between two pongs."""
    with pytest.raises(ValueError, match="max_silence"):
        _policy(max_silence_ns=10 * SECOND_NS)  # the ping interval is 15 s


@pytest.mark.trace("REQ-WP-078")
def test_a_silence_limit_longer_than_the_keepalive_is_accepted() -> None:
    assert _policy(max_silence_ns=60 * SECOND_NS).max_silence_ns == 60 * SECOND_NS


@pytest.mark.trace("REQ-WP-078")
def test_the_backoff_ceiling_cannot_be_below_the_minimum_interval() -> None:
    with pytest.raises(ValueError, match="backoff"):
        _policy(min_connect_interval_ns=10 * SECOND_NS, max_connect_backoff_ns=5 * SECOND_NS)


@pytest.mark.trace("REQ-WP-078")
def test_the_default_ceiling_is_a_minute() -> None:
    assert _policy().max_connect_backoff_ns == 60 * SECOND_NS
