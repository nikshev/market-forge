"""The volume profile as the API serves it: a window of stored price bins, as of an instant.

# @trace: REQ-WP-089

PRD section 14.1 asks for profiles over rolling 4h, 24h and 7d. The price bins are collected from
the moment the ingest was deployed (there is no history, and none is inferred from bars), so a
profile **says how much of its window the data covers**: a 24h profile from three hours of data
reports three hours, and `complete` is false. It is never presented as the full window when it is
not.

A profile as of `t` is built from whole blocks closed at or before `t` over `(effective - window,
effective]`, where `effective` is the close of the latest such block: the window is of blocks, not
of the instant. The POC and the value area come from the same code as the trade-level profile
(`volume.profile.from_bins`, ADR-028).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from channelflow.tables.volume_bins import BinsRead
from channelflow.volume.profile import VolumeProfile, from_bins

HOUR_NS = 3_600_000_000_000

#: PRD section 14.1's profile windows. This module is their vocabulary, as `timeframes.py` is the
#: bar timeframes': a different thing, kept apart (a window is how far back a profile looks).
ProfileWindow = Literal["4h", "24h", "7d"]

#: The windows by their token. Anything else is refused at the route.
WINDOWS: dict[str, int] = {"4h": 4 * HOUR_NS, "24h": 24 * HOUR_NS, "7d": 7 * 24 * HOUR_NS}


class ProfileUnavailable(LookupError):
    """There are no price bins for the series (yet): nothing to describe, not an empty profile."""


@dataclass(frozen=True)
class WindowedProfile:
    profile: VolumeProfile
    as_of_ns: int
    window_ns: int
    #: The open of the earliest block in the window.
    covers_from_ns: int
    #: How much of the window the data covers, up to the whole window.
    covered_ns: int
    complete: bool
    left_out_rows: int


def windowed_profile(read: BinsRead, *, window_ns: int) -> WindowedProfile:
    """The profile of rows already selected for a window, with how much of the window they cover."""
    if not read.rows or read.as_of_ns is None:
        raise ProfileUnavailable("no price bins for this series")
    width = read.rows[0].bin_width
    profile = from_bins(read.rows, bin_width=width)
    covers_from = min(row.block_open_time_ns for row in read.rows)
    return WindowedProfile(
        profile=profile,
        as_of_ns=read.as_of_ns,
        window_ns=window_ns,
        covers_from_ns=covers_from,
        covered_ns=min(window_ns, read.as_of_ns - covers_from),
        complete=covers_from <= read.as_of_ns - window_ns,
        left_out_rows=read.left_out_rows,
    )
