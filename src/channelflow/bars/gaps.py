# @trace: REQ-WP-087

"""Whether a hole sits between two bars (REQ-WP-087).

FR-001 and FR-006 of the detector/channel gap policy: both models detect a
hole from the bars they are given rather than trusting the caller, and how
many missing bars make a hole is configuration (Principle X).

    missing = round((next.open_time_ns - prev.close_time_ns) / timeframe_ns)
    a hole  = missing > threshold

Contiguous bars open where the previous closed, so `missing` is 0 and the
answer is False at any non-negative threshold. The default threshold of 1
bridges exactly one missing bar and restarts at two; 0 restarts on any
positive distance.

A distance of zero or less -- a corrected bar reissued on the previous bar's
own timestamps, or an overlap -- is not a hole: bars arriving late are a
repair, not bars absent from the middle of the series, and `missing` is never
allowed to go negative. A non-positive `timeframe_ns` has no meaning as a
step and raises rather than dividing by zero or running backwards.

Placement note (T006 in tasks.md names `extrema/detector.py`): the helper
serves the detector *and* the channel fit, and both take their bars from
`channelflow.bars`. It lives here so `channels/` never has to import from
`extrema/` -- one model family reaching into another would be the wrong
dependency direction, and it would put a cycle one refactor away (the
detector already takes channel width as an input).

Only `open_time_ns`, `close_time_ns` and `timeframe_ns` are read, so the
decision uses nothing later than the two bars themselves: no look-ahead by
construction, live and replay alike.
"""

from __future__ import annotations

from channelflow.bars.models import Bar

__all__ = ["is_gap"]


def is_gap(prev_bar: Bar, next_bar: Bar, timeframe_ns: int, threshold: int = 1) -> bool:
    """True when more than `threshold` bars are missing between the two bars.

    `timeframe_ns` is the step the series is counted in -- one hole is "N
    missing bars", never "N nanoseconds" -- and `threshold` is how many of
    them may be missing before the models restart (default 1, from
    `CHANNELFLOW_GAP_THRESHOLD`).

    Raises ValueError on a non-positive `timeframe_ns`: a hole measured in
    steps of zero or of a negative step cannot be counted, and silently
    treating it as contiguous would bridge the very outage the models are
    meant to stop at.
    """
    if timeframe_ns <= 0:
        raise ValueError(
            f"timeframe_ns must be positive, got {timeframe_ns!r}; "
            "a hole cannot be counted in steps of zero or of a negative step"
        )

    distance = next_bar.open_time_ns - prev_bar.close_time_ns
    if distance <= 0:
        # Corrected or overlapping bar, not missing bars: the gap size would
        # otherwise go negative and pass every threshold as "not a hole",
        # which is the right answer for the wrong reason.
        return False

    missing = round(distance / timeframe_ns)
    return missing > threshold
