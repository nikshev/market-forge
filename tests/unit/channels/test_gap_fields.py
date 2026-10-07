"""The channel snapshot says what its window held (REQ-WP-087).

FR-004, FR-005: the channel is fitted only to bars after a hole, so a snapshot
has to state how many bars that window actually held, whether it is shorter
than the `lookback` it asked for, and where the window begins after the hole.
Without those three numbers a short, post-gap window is indistinguishable from
the model's regular one, which is exactly the presentation the requirement
forbids -- a number built on one side of a hole must never look like one built
on a continuous series.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from channelflow.channels import ChannelQuality, ChannelSnapshot

MINUTE_NS = 60 * 1_000_000_000
AS_OF_NS = 1_788_838_800_000_000_000
#: The window restarts three minutes before `as_of_ns`: the first bar of a
#: window that began after a hole.
GAP_NS = AS_OF_NS - 3 * MINUTE_NS


def snapshot(**overrides: object) -> ChannelSnapshot:
    fields: dict[str, object] = {
        "as_of_ns": AS_OF_NS,
        "model_name": "test",
        "model_version": "1.0.0",
        "lookback": 60,
        "center_now": 100.0,
        "upper_now": 105.0,
        "lower_now": 95.0,
        "slope_normalized": 0.5,
        "width_pct": 10.0,
        "quality": ChannelQuality(score=0.8, submetrics={}, contributing=(), unavailable=()),
        "source_max_event_time_ns": AS_OF_NS - MINUTE_NS,
    }
    fields.update(overrides)
    return ChannelSnapshot(**fields)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-087")
def test_the_snapshot_states_how_many_bars_its_window_held() -> None:
    """FR-005, SC-002: the three window fields exist, round-trip, and a
    construction that says nothing about its window keeps claiming the full
    window it claimed before the fields existed.

    `window_bars` defaults to `lookback` rather than to 0 because every
    snapshot produced so far went through `fit_window`, which refuses to fit
    on fewer bars than the lookback asks for -- so "no window stated" has
    always meant the full one, and defaulting otherwise would quietly turn
    every existing full-window snapshot into a claim of zero bars.
    """
    fitted = snapshot(window_bars=45, window_short=True, first_bar_after_gap_ns=GAP_NS)

    assert fitted.window_bars == 45
    assert fitted.window_short is True
    assert fitted.first_bar_after_gap_ns == GAP_NS

    # Round-trips: the snapshot a chart or a backtest reads back carries the
    # window it was fitted on. Frozen plus extra="forbid" mean a different
    # constructor path is the only way to lose a field.
    again = ChannelSnapshot.model_validate(fitted.model_dump())

    assert again == fitted
    assert again.window_bars == 45
    assert again.window_short is True
    assert again.first_bar_after_gap_ns == GAP_NS

    # No gap in the window, and no window stated: both are honestly absent
    # rather than invented.
    unmigrated = snapshot()

    assert unmigrated.window_bars == unmigrated.lookback
    assert unmigrated.window_short is False
    assert unmigrated.first_bar_after_gap_ns is None


@pytest.mark.trace("REQ-WP-087")
def test_window_short_says_whether_the_window_is_shorter_than_the_lookback() -> None:
    """FR-005: `window_short` is `window_bars < lookback`, so a producer that
    states a short window gets the flag, and one that contradicts it is
    refused rather than stored.

    A snapshot claiming 45 bars while saying the window was not short would be
    the same dishonesty in two fields, and the model is the last place it can
    be caught -- everything downstream reads the claim, not the bars.
    """
    assert snapshot(window_bars=45).window_short is True
    assert snapshot(window_bars=60).window_short is False
    assert snapshot(window_bars=45, window_short=True).window_short is True

    with pytest.raises(ValidationError):
        snapshot(window_bars=45, window_short=False)

    with pytest.raises(ValidationError):
        snapshot(window_bars=61)
