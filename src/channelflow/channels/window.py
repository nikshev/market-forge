"""The bars a channel fit may see.

# @trace: REQ-WP-006
# @trace: REQ-CHAN-001
# @trace: REQ-WP-087

Extracted so every baseline uses one implementation rather than four that agree
today. PRD section 13.1's invariant is `source_max_event_time <= as_of`, section
2.1 calls repainting the critical risk the product exists to avoid, and
Constitution Principle I adds that the rule holds "even when violating it would
improve a backtest".

The filtering belongs to the fitter, not the caller. A channel fitted with
hindsight looks superb, which is exactly why the guard cannot be somebody's
responsibility to remember.
"""

from __future__ import annotations

from channelflow.bars import Bar
from channelflow.bars.gaps import is_gap


class ChannelFitError(ValueError):
    """The channel could not be fitted, and the reason is named.

    Raised rather than returning a degraded snapshot: a channel fitted on fewer
    points than asked for is a different model wearing the same name.
    """


def _find_gap_boundary(bars: list[Bar], lookback: int) -> int:
    """Find the index of the first bar after the last gap within the lookback window.

    Returns the index in the eligible bars list where the window should start.
    If no gap is found within the lookback, returns 0 (start from the beginning
    of the eligible bars for a full lookback window).
    """
    # We need at least 2 bars to detect a gap
    if len(bars) < 2:
        return 0

    # Check for gaps from the end of the series backwards
    # A gap is detected when next_bar.open - prev.close > threshold * timeframe
    for i in range(len(bars) - 1, 0, -1):
        prev = bars[i - 1]
        curr = bars[i]
        # Default threshold is 1 (same as detector)
        if is_gap(prev, curr, curr.timeframe_ns, threshold=1):
            # Gap found: window should start at curr (index i)
            return i

    return 0


def fit_window(bars: list[Bar], *, as_of_ns: int, lookback: int) -> list[Bar]:
    """The most recent `lookback` finalized bars at or before `as_of_ns`.

    Three filters, each one a requirement rather than a precaution: finalized
    only (PRD section 12), at or before `as_of` (section 13.1), and ordered by
    event time (arrival order is not market information).

    If a gap is detected within the lookback window, the window starts at the
    first bar after the gap. If fewer than `lookback` bars are available after
    the gap, the window is shortened accordingly (REQ-WP-087).
    """
    eligible = sorted(
        (b for b in bars if b.is_final and b.close_time_ns <= as_of_ns),
        key=lambda b: b.close_time_ns,
    )

    # Find where the window should start (after any gap)
    start_idx = _find_gap_boundary(eligible, lookback)
    window_bars = eligible[start_idx:]
    gap_detected = start_idx > 0

    # Take at most `lookback` bars from the start index
    window = window_bars[-lookback:]

    # REQ-WP-087: Allow short windows only when a gap was detected.
    # Otherwise, require full lookback (original behavior for no-gap case).
    if len(window) < lookback:
        if gap_detected:
            # Short window allowed due to gap (REQ-WP-087)
            pass
        else:
            raise ChannelFitError(
                f"need {lookback} finalized bars at or before as_of, found {len(window)}; "
                "fitting on fewer would silently be a different model"
            )
    if not window:
        raise ChannelFitError("need at least 1 finalized bar at or before as_of, found 0")
    for bar in window:
        if bar.close <= 0:
            raise ChannelFitError(
                f"bar at {bar.open_time_ns} has a non-positive close ({bar.close}); "
                "log price is undefined"
            )
    return window
