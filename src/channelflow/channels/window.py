"""The bars a channel fit may see.

# @trace: REQ-WP-006
# @trace: REQ-CHAN-001

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


class ChannelFitError(ValueError):
    """The channel could not be fitted, and the reason is named.

    Raised rather than returning a degraded snapshot: a channel fitted on fewer
    points than asked for is a different model wearing the same name.
    """


def fit_window(bars: list[Bar], *, as_of_ns: int, lookback: int) -> list[Bar]:
    """The most recent `lookback` finalized bars at or before `as_of_ns`.

    Three filters, each one a requirement rather than a precaution: finalized
    only (PRD section 12), at or before `as_of` (section 13.1), and ordered by
    event time (arrival order is not market information).
    """
    eligible = sorted(
        (b for b in bars if b.is_final and b.close_time_ns <= as_of_ns),
        key=lambda b: b.close_time_ns,
    )
    window = eligible[-lookback:]

    if len(window) < lookback:
        raise ChannelFitError(
            f"need {lookback} finalized bars at or before as_of, found {len(window)}; "
            "fitting on fewer would silently be a different model"
        )
    for bar in window:
        if bar.close <= 0:
            raise ChannelFitError(
                f"bar at {bar.open_time_ns} has a non-positive close ({bar.close}); "
                "log price is undefined"
            )
    return window
