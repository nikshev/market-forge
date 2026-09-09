"""The channel that existed, against the model's later state.

# @trace: REQ-US-003

REQ-US-003, in the researcher's own words: "compare the historical snapshot of
the channel that actually existed at that moment against the model's later
state". PRD section 27.5 calls the distinction critical because it "directly
exposes repaint-like differences and protects research integrity".

`channels.py` serves either view on its own, and caps its refit at the requested
instant -- two views of one information set, which measures model drift. This
module answers the other half of section 27.5: a refit over history up to a
*later* instant, which has seen what followed ([[ADR-046]]).

That hindsight is the subject of the measurement, so every comparison states how
much of it there was and declares itself research-only. A channel fitted over
later bars will often look like it predicted what followed; carried anywhere near
a signal it is a look-ahead with a plausible face. A test walks the signal,
alerting, stop and extrema packages asserting none of them mentions this module
-- the same device [[ADR-040]] uses for lead-lag, because intent is not
checkable and a fact about the source tree is.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.api.channels import ChannelUnavailable, channel_at
from channelflow.api.repositories import Repository
from channelflow.channels import ChannelSnapshot, RollingOLSChannel


class HindsightInverted(ValueError):
    """The "later" instant is earlier than the one being compared against."""


@dataclass(frozen=True)
class ChannelDifference:
    """What moved between the two channels."""

    center: float
    upper: float
    lower: float
    slope: float
    width_pct: float
    quality: float
    #: The centre's movement as a share of the stored channel's own width.
    #: `None` when that width is zero: dividing by it reports an infinite
    #: repaint, which reads as a catastrophe rather than as a flat channel.
    center_in_widths: float | None


@dataclass(frozen=True)
class ChannelComparison:
    """Both channels, their difference, and how much hindsight the second had."""

    as_seen_then: ChannelSnapshot
    current_refit: ChannelSnapshot
    difference: ChannelDifference
    #: How far past the compared instant the refit was allowed to see. Zero
    #: means the two channels saw one information set, and any difference
    #: belongs to the model rather than to the data.
    hindsight_ns: int
    #: Never omitted and never false. See the module docstring.
    research_only: bool = True


def compare_channel(
    repository: Repository,
    *,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    at_ns: int,
    now_ns: int,
    model: RollingOLSChannel | None = None,
) -> ChannelComparison:
    """The stored snapshot at `at_ns` against a refit over history up to `now_ns`.

    Raises rather than approximating on either side. A missing snapshot cannot
    be rebuilt -- that is the guarantee `AS-SEEN-THEN` exists to make -- and a
    refit over too little history would put a different model beside a real one
    under the same name.
    """
    if now_ns < at_ns:
        raise HindsightInverted(
            f"the later instant {now_ns} is before {at_ns}; a later state that is "
            "earlier is not one, and the difference would carry the wrong sign"
        )

    stored = channel_at(
        repository,
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        at_ns=at_ns,
        as_seen_then=True,
    ).snapshot
    refit = channel_at(
        repository,
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        at_ns=now_ns,
        as_seen_then=False,
        model=model,
    ).snapshot

    return ChannelComparison(
        as_seen_then=stored,
        current_refit=refit,
        difference=_difference(stored, refit),
        hindsight_ns=now_ns - at_ns,
    )


def _difference(stored: ChannelSnapshot, refit: ChannelSnapshot) -> ChannelDifference:
    width = stored.upper_now - stored.lower_now
    center = refit.center_now - stored.center_now
    return ChannelDifference(
        center=center,
        upper=refit.upper_now - stored.upper_now,
        lower=refit.lower_now - stored.lower_now,
        slope=refit.slope_normalized - stored.slope_normalized,
        width_pct=refit.width_pct - stored.width_pct,
        quality=refit.quality.score - stored.quality.score,
        center_in_widths=None if width == 0.0 else center / width,
    )


__all__ = [
    "ChannelComparison",
    "ChannelDifference",
    "ChannelUnavailable",
    "HindsightInverted",
    "compare_channel",
]
