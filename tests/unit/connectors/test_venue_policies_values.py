"""The policy the live daemon reads, pinned (REQ-WP-078).

# @trace: REQ-WP-078

Read through `VENUE_REGISTRY`, which is what `build_daemon` uses, and not through the
constants in `session.py`: the earlier tests pinned the constants while the daemon read
a different set.

Why these values and not the ones the registry carried:

* **Binance** has a 24-hour stream *lifetime* and no idle timeout. `venue.py` had them
  the other way round, which made the daemon's silence threshold 48 hours and stopped
  the 24-hour reconnect `tick` was written to perform.
* **Bybit** closed an idle connection at 60.7 s with no close frame; the policy is 60 s,
  the observation rounded down.
* **OKX** closes with "No data received in 30s"; the policy is 30 s, the venue's own
  figure. Its ping is 15 s: `session.py` records that fifteen seconds was measured to
  survive a hundred, and twenty was not measured against a 30-second limit.
"""

from __future__ import annotations

import pytest

from channelflow.connectors.session import SECOND_NS
from channelflow.connectors.venue import VENUE_REGISTRY


@pytest.mark.trace("REQ-WP-078")
def test_binance_has_a_lifetime_and_no_idle_timeout() -> None:
    policy = VENUE_REGISTRY["binance"].policy

    assert policy.stream_lifetime_ns == 24 * 60 * 60 * SECOND_NS
    assert policy.idle_timeout_ns is None


@pytest.mark.trace("REQ-WP-078")
def test_bybit_pings_every_twenty_seconds_against_a_sixty_second_limit() -> None:
    policy = VENUE_REGISTRY["bybit"].policy

    assert policy.idle_timeout_ns == 60 * SECOND_NS
    assert policy.client_ping_interval_ns == 20 * SECOND_NS


@pytest.mark.trace("REQ-WP-078")
def test_okx_pings_every_fifteen_seconds_against_a_thirty_second_limit() -> None:
    policy = VENUE_REGISTRY["okx"].policy

    assert policy.idle_timeout_ns == 30 * SECOND_NS
    assert policy.client_ping_interval_ns == 15 * SECOND_NS


@pytest.mark.trace("REQ-WP-078")
@pytest.mark.parametrize("venue", ["binance", "bybit", "okx"])
def test_each_live_venue_has_a_silence_limit_with_a_basis(venue: str) -> None:
    """60 s. The longest real gaps measured on 2026-10-02 were 22.2 s (Bybit BTCUSDT, 360
    minutes) and 11.2 s (SOLUSDT, 309 minutes); a 64.1 s gap in the first was this
    project's own container restart and is not a basis for anything."""
    policy = VENUE_REGISTRY[venue].policy

    assert policy.max_silence_ns == 60 * SECOND_NS
