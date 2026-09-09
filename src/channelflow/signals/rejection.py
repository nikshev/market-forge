"""Rejection detectors (PRD section 21.3).

# @trace: REQ-WP-007
# @trace: REQ-EXP-003

Pluggable, because section 21.3 lists four and only one is buildable now: the
other three depend on section 21.4's confirmation features, which need work
packages that do not exist. FR-013 makes them additions rather than rewrites.
"""

from __future__ import annotations

from typing import Protocol

from channelflow.bars import Bar
from channelflow.channels import ChannelSnapshot


class RejectionDetector(Protocol):
    """Decides whether a touched candidate has rejected off its boundary."""

    name: str

    def rejected(
        self, bar: Bar, channel: ChannelSnapshot, *, boundary: str, direction: str
    ) -> bool: ...


class CloseBackInside:
    """PRD section 21.3's first detector: price closed back inside the channel.

    The threshold is a fraction of channel width rather than an absolute
    distance, so the same configuration means the same thing on a symbol at
    78,000 and one at 0.4.
    """

    name = "close_back_inside"

    def __init__(self, min_distance_pct_of_width: float = 0.15) -> None:
        self.min_distance_pct_of_width = min_distance_pct_of_width

    def rejected(
        self, bar: Bar, channel: ChannelSnapshot, *, boundary: str, direction: str
    ) -> bool:
        width = channel.upper_now - channel.lower_now
        if width <= 0:
            return False
        close = float(bar.close)
        margin = width * self.min_distance_pct_of_width

        if boundary == "upper":
            return close < channel.upper_now - margin
        if boundary == "lower":
            return close > channel.lower_now + margin
        # Middle-line continuation: rejection is failure to hold the middle in
        # the direction the channel is going.
        middle = (channel.upper_now + channel.lower_now) / 2
        return close < middle - margin if direction == "short" else close > middle + margin


class WickOnly:
    """PRD section 21.3's wick test: "upper wick/body ratio above threshold".

    The most permissive of the four detectors -- it asks only what the bar's own
    shape says, with no memory and no confirmation. That is the point of having
    it in REQ-EXP-003's comparison: it confirms earliest and, if the others earn
    their extra bar, least reliably.

    A bar with no body and a wick is a rejection, not a division by zero: a
    doji that spiked through the boundary and came back is the shape this
    detector exists to catch.
    """

    name = "wick_only"

    def __init__(self, min_wick_body_ratio: float = 1.0) -> None:
        self.min_wick_body_ratio = min_wick_body_ratio

    def rejected(
        self, bar: Bar, channel: ChannelSnapshot, *, boundary: str, direction: str
    ) -> bool:
        open_, close = float(bar.open), float(bar.close)
        high, low = float(bar.high), float(bar.low)
        body = abs(close - open_)
        wick = high - max(open_, close) if direction == "short" else min(open_, close) - low
        if wick <= 0.0:
            return False
        if body <= 0.0:
            return True
        return wick / body >= self.min_wick_body_ratio


class TwoBarConfirmation:
    """PRD section 21.3's alternative: "next bar closes lower".

    One bar of memory, which is what "next bar" means and what the single-bar
    detectors cannot express. The machine holds one candidate at a time and the
    backtest runner copies its machine per run, so that memory is per-run rather
    than shared between them.

    Slower than `WickOnly` by construction: it cannot answer on the first bar it
    sees, because there is no previous close to compare against.
    """

    name = "two_bar_confirmation"

    def __init__(self) -> None:
        self._previous_close: float | None = None

    def rejected(
        self, bar: Bar, channel: ChannelSnapshot, *, boundary: str, direction: str
    ) -> bool:
        close = float(bar.close)
        previous, self._previous_close = self._previous_close, close
        if previous is None:
            return False
        return close < previous if direction == "short" else close > previous
