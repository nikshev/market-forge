"""The timeframe vocabulary every producer, read and view shares.

# @trace: REQ-WP-073
# @trace: REQ-WP-074

A `Timeframe` is a duration **and the instant its windows are aligned to**:

    window_start(t) = ((t - origin_ns) // ns) * ns + origin_ns

Every timeframe but the week has `origin_ns = 0`, where this reduces to the
epoch alignment `BarBuilder` already uses. The week does not: 1 January 1970 was
a Thursday, so floor division alone puts weekly boundaries on Thursdays when a
weekly bar opens Monday 00:00 UTC.

Floor division, deliberately: for `t < origin_ns` this must round toward
negative infinity. Pinned by a test, because the same arithmetic is destined for
TypeScript, where `/` truncates.

**This module is the vocabulary, not the set a deployment produces.** Which
timeframes are built comes from `CHANNELFLOW_TIMEFRAMES`; knowing the spelling
`4h` is what parsing that configuration requires, not a claim that this stack
always builds one.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

#: A token that names a calendar period rather than a duration. `m` lower-case
#: is a minute; `M` upper-case is a month, a year is `y`. A calendar month is
#: 28, 29, 30 or 31 days, so it has no nanosecond value at all -- and neither
#: does a year, for the same leap-day reason.
_CALENDAR_TOKEN = re.compile(r"^\d+[MyY]$")


@dataclass(frozen=True)
class Timeframe:
    token: str
    ns: int
    origin_ns: int

    def __post_init__(self) -> None:
        if self.ns <= 0:
            raise ValueError(f"timeframe ns must be positive, got {self.ns}")
        if not (0 <= self.origin_ns < self.ns):
            raise ValueError(f"origin_ns must be in [0, ns), got {self.origin_ns} for ns={self.ns}")

    def window_start(self, t_ns: int) -> int:
        """The opening instant of the window `t_ns` falls in."""
        return ((t_ns - self.origin_ns) // self.ns) * self.ns + self.origin_ns


class UnknownTimeframe(ValueError):
    """A token that is neither known nor a calendar period."""

    def __init__(self, token: str, known: tuple[str, ...]):
        super().__init__(f"unknown timeframe: {token}. known: {', '.join(known)}")
        self.token = token
        self.known = known


class CalendarPeriod(ValueError):
    """A token whose period has no fixed duration in nanoseconds."""

    def __init__(self, token: str):
        super().__init__(
            f"{token}: a calendar period has no fixed duration -- a month is 28, "
            "29, 30 or 31 days -- so it cannot be expressed as nanoseconds"
        )
        self.token = token


#: The known tokens. `1w` carries the Monday origin; every other carries zero.
TIMEFRAMES = {
    "1m": Timeframe("1m", 60_000_000_000, 0),
    "5m": Timeframe("5m", 300_000_000_000, 0),
    "15m": Timeframe("15m", 900_000_000_000, 0),
    "30m": Timeframe("30m", 1_800_000_000_000, 0),
    "1h": Timeframe("1h", 3_600_000_000_000, 0),
    "4h": Timeframe("4h", 14_400_000_000_000, 0),
    "1d": Timeframe("1d", 86_400_000_000_000, 0),
    "1w": Timeframe("1w", 604_800_000_000_000, 345_600_000_000_000),
}

#: What every target is built from: the ingest daemon writes one-minute bars and
#: nothing resamples them into themselves.
SOURCE_TOKEN = "1m"


def parse(token: str) -> Timeframe:
    """A configured token as a `Timeframe`, or a refusal that teaches."""
    known = TIMEFRAMES.get(token)
    if known is not None:
        return known
    if _CALENDAR_TOKEN.match(token):
        raise CalendarPeriod(token)
    raise UnknownTimeframe(token, tuple(sorted(TIMEFRAMES)))


def parse_list(text: str) -> tuple[Timeframe, ...]:
    """A comma-separated configuration, sorted by duration and de-duplicated.

    An empty result raises: a deployment configured to produce no timeframes is
    a mistake that from the outside looks exactly like a quiet market.
    """
    tokens = [part.strip() for part in text.split(",") if part.strip()]
    if not tokens:
        raise ValueError("timeframe list is empty")
    unique = {tf.token: tf for tf in (parse(token) for token in tokens)}
    return tuple(sorted(unique.values(), key=lambda tf: tf.ns))


def offered(configured: Sequence[Timeframe]) -> tuple[Timeframe, ...]:
    """What a deployment can serve: the source plus its configured targets.

    The source joins unconditionally. `CHANNELFLOW_TIMEFRAMES` names what
    *resampling* builds and excludes `1m` by design, but §5.1 names `1m` among
    the Phase 1 timeframes and the ingest daemon always produces it -- so a
    view of the set that omitted it would hide the one series guaranteed to
    exist. Listing it again is harmless: the union de-duplicates by token.
    """
    unique = {tf.token: tf for tf in (*configured, TIMEFRAMES[SOURCE_TOKEN])}
    return tuple(sorted(unique.values(), key=lambda tf: tf.ns))
