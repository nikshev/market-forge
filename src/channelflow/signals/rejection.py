"""Rejection detectors (PRD section 21.3).

# @trace: REQ-WP-007

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
