"""The channel cannot see the future (REQ-WP-006).

PRD section 13.1 states the invariant `source_max_event_time <= as_of`, and
section 2.1 identifies repainting as the critical risk this product exists to
avoid. Constitution Principle I adds that the rule holds "even when violating it
would improve a backtest" -- which is precisely the temptation a channel model
presents, since a line fitted with hindsight looks superb.

This file is separate from the rest so its absence would be obvious.
"""

from __future__ import annotations

import pytest

from channelflow.channels import RollingOLSChannel
from tests.unit.channels.conftest import log_linear_series, make_bar


@pytest.mark.trace("REQ-WP-006")
def test_appending_future_bars_does_not_change_a_past_snapshot(trending: list) -> None:
    """SC-001. The only test that actually proves non-repainting: fit, then let
    the future arrive, then refit the same moment and demand the same answer."""
    model = RollingOLSChannel(lookback=60)
    as_of_ns = trending[79].close_time_ns

    before = model.fit(trending[:80], as_of_ns=as_of_ns)
    # index_offset matters: without it the 'future' bars reuse the original
    # timestamps and land inside the window, so the test would pass for the
    # wrong reason -- or fail for one, as it did.
    later = trending + log_linear_series(
        40, start=999.0, slope_per_bar=0.05, index_offset=len(trending)
    )
    after = model.fit(later, as_of_ns=as_of_ns)

    assert after == before, (
        "the channel at a past moment changed when later bars arrived -- this is "
        "repainting, and it is the failure the whole product exists to prevent"
    )


@pytest.mark.trace("REQ-WP-006")
def test_the_hard_invariant_holds(trending: list) -> None:
    """SC-002. PRD section 13.1's stated invariant, checked at every offset."""
    model = RollingOLSChannel(lookback=30)
    for i in range(40, len(trending)):
        as_of_ns = trending[i].close_time_ns
        snapshot = model.fit(trending, as_of_ns=as_of_ns)
        assert snapshot.source_max_event_time_ns <= snapshot.as_of_ns


@pytest.mark.trace("REQ-WP-006")
def test_bars_after_as_of_are_excluded_not_trusted(trending: list) -> None:
    """FR-008. The model filters rather than trusting its caller to have done
    so -- a caller who forgets produces a channel that peeks and looks better."""
    model = RollingOLSChannel(lookback=30)
    as_of_ns = trending[59].close_time_ns

    from_full_history = model.fit(trending, as_of_ns=as_of_ns)
    from_truncated = model.fit(trending[:60], as_of_ns=as_of_ns)

    assert from_full_history == from_truncated


@pytest.mark.trace("REQ-WP-006")
def test_unfinalized_bars_are_excluded(trending: list) -> None:
    """FR-009. PRD section 12: signals use finalized bars by default. Enforcing
    it here means a caller cannot forget it."""
    model = RollingOLSChannel(lookback=30)
    as_of_ns = trending[59].close_time_ns
    # Excluding a bar shifts the window by one, so the comparison is against a
    # history that genuinely lacks that bar -- not against one that has it.
    without_it = model.fit(trending[:59], as_of_ns=as_of_ns)

    with_forming = list(trending[:59])
    with_forming.append(make_bar(index=59, close=99999.0, is_final=False))

    assert model.fit(with_forming, as_of_ns=as_of_ns) == without_it, (
        "an unfinalized bar changed the fit; PRD section 12 says signals use "
        "finalized bars, and a forming bar's close is not yet a close"
    )
