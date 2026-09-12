"""Cross-venue funding dispersion, over a common interval or not at all.

# @trace: REQ-WP-050

PRD section 16.1 lists "cross-venue funding dispersion" among the derivatives
features. The feature is one line; the reason it needs a module is that **the
rates are not comparable as they arrive.**

Measured from each venue's own funding history on 2026-09-12:

    Hyperliquid    60 minutes
    Binance       480 minutes
    Bybit         480 minutes
    OKX           480 minutes

A Hyperliquid rate is an hourly rate and the other three are eight-hourly. Put
side by side without normalising, the four differ by a factor of eight before
the market has said anything — and the resulting figure is positive, ordered,
believable, and moves when funding moves. It looks like a signal and behaves
like one, which is the worst combination available.

**The interval is observed, never assumed.** Eight hours is the common case and
that is exactly why a default would be dangerous: right for three venues,
silently wrong for the fourth, wrong again for the next venue that settles
hourly. `settlement_interval_ns` derives it from a venue's own settlement
timestamps and refuses a schedule too irregular to describe with one number.

**Staleness excludes rather than carries forward**, as [[REQ-WP-016]]'s
consensus does. The tolerance is the venue's own interval rather than a constant:
a reading older than that means the venue has settled again since, so the rate in
hand is not the rate in force. Nothing arbitrary to tune, and it scales with the
venue.

**One venue is not a dispersion**, for the reason the consensus mid gives about a
median over one venue.

**What "dispersion" means is not stated by the PRD**, so this reports three
figures rather than choosing one: where the middle is, how far apart the ends
are, and how tightly the venues cluster. A single number would hide which was
meant. All three are signed-aware — a dispersion over absolute values would call
a market where two venues pay longs and two pay shorts "tight".
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

#: Funding rates are fractions; everything reported here is in basis points.
BPS = 10_000

MS_TO_NS = 1_000_000

#: How far consecutive settlements may drift from the median gap and still be
#: called one schedule. Binance's own history carries 479- and 480-minute gaps,
#: so a venue is not required to be exact -- only regular.
SCHEDULE_TOLERANCE = 0.05


class NoDispersion(ValueError):
    """Fewer than two venues could contribute.

    A dispersion over one venue is that venue's funding rate wearing a better
    name, which is [[REQ-WP-016]]'s objection to a median over one mid.
    """


class IrregularSchedule(ValueError):
    """The settlements are too uneven to describe with a single interval.

    Refused rather than averaged. A venue that settles on an irregular schedule
    has no "rate per eight hours" to compare, and inventing one would be the
    error this module exists to prevent, arrived at from the other direction.
    """


@dataclass(frozen=True)
class VenueFunding:
    """One venue's funding rate, with the period it covers.

    `interval_ns` has no default and is not optional. The rate means nothing
    without it, and the shape of this type is what stops a caller supplying the
    first and forgetting the second.
    """

    venue_id: str
    #: Signed, as the venue publishes it. Funding is negative when shorts pay.
    rate: float
    interval_ns: int
    observed_at_ns: int

    def __post_init__(self) -> None:
        if self.interval_ns <= 0:
            raise ValueError(f"{self.venue_id}: a funding interval of {self.interval_ns} is none")


@dataclass(frozen=True)
class FundingDispersion:
    """What the venues disagree about, and who was asked.

    Shaped after [[REQ-WP-016]]'s `Consensus`: the figures are useless without
    knowing who contributed and who did not, and why.
    """

    #: Every figure is per `interval_ns`, in basis points.
    interval_ns: int
    median_bps: float
    spread_bps: float
    stdev_bps: float
    per_venue_bps: dict[str, float]
    contributors: tuple[str, ...]
    excluded: dict[str, str]

    @property
    def contributor_count(self) -> int:
        return len(self.contributors)


def settlement_interval_ns(settlement_times_ms: Sequence[int]) -> int:
    """The gap between settlements, from a venue's own timestamps.

    The median gap rather than the first, because a venue's schedule carries
    jitter -- Binance's own history has 479- and 480-minute gaps -- and the first
    gap is one observation.

    Refuses when the gaps are further apart than `SCHEDULE_TOLERANCE`. A venue
    that settles irregularly has no single interval, and returning the median
    anyway would hand back a number that looks like one.
    """
    stamps = sorted(settlement_times_ms)
    if len(stamps) < 3:
        raise IrregularSchedule(
            f"{len(stamps)} settlement(s) show at most one gap; an interval needs "
            "more than a single observation"
        )
    gaps = [later - earlier for earlier, later in zip(stamps, stamps[1:], strict=False)]
    if any(gap <= 0 for gap in gaps):
        raise IrregularSchedule("settlements are not strictly increasing")

    middle = statistics.median(gaps)
    for gap in gaps:
        if abs(gap - middle) / middle > SCHEDULE_TOLERANCE:
            raise IrregularSchedule(
                f"gaps range from {min(gaps)}ms to {max(gaps)}ms around a median of "
                f"{middle}ms; that is not one schedule"
            )
    return int(middle) * MS_TO_NS


def normalise(rate: float, *, from_interval_ns: int, to_interval_ns: int) -> float:
    """A rate for one period expressed over another, in basis points.

    Linear, not compounded. Funding accrues per period and is paid, not
    reinvested, so eight hourly payments are eight times one hourly payment --
    and compounding them would be modelling a position that rolls its funding
    back in, which is a different instrument.
    """
    if from_interval_ns <= 0 or to_interval_ns <= 0:
        raise ValueError("an interval of zero describes no period")
    return rate * BPS * (to_interval_ns / from_interval_ns)


def funding_dispersion(
    readings: Sequence[VenueFunding],
    *,
    at_ns: int,
    to_interval_ns: int,
) -> FundingDispersion:
    """How far apart the venues' funding is, over one common interval.

    `to_interval_ns` has no default. Annualising is the conventional choice and
    it bakes in 365 days against 360 and simple against compounded, which
    belongs to whoever reads the number rather than to this function.
    """
    if to_interval_ns <= 0:
        raise ValueError("a dispersion needs an interval to express itself over")

    excluded: dict[str, str] = {}
    eligible: list[VenueFunding] = []
    for reading in readings:
        if reading.observed_at_ns > at_ns:
            excluded[reading.venue_id] = "reading is later than the instant asked about"
            continue
        age_ns = at_ns - reading.observed_at_ns
        if age_ns > reading.interval_ns:
            # The venue has settled again since, so the rate in hand is not the
            # rate in force. Carrying it forward would narrow the dispersion by
            # pretending a venue agrees.
            excluded[reading.venue_id] = (
                f"reading is {age_ns}ns old, past this venue's own {reading.interval_ns}ns interval"
            )
            continue
        eligible.append(reading)

    if len(eligible) < 2:
        raise NoDispersion(
            f"only {len(eligible)} venue(s) could contribute at {at_ns}; a dispersion "
            "over one venue is that venue's funding rate wearing a better name"
        )

    per_venue = {
        reading.venue_id: normalise(
            reading.rate,
            from_interval_ns=reading.interval_ns,
            to_interval_ns=to_interval_ns,
        )
        for reading in eligible
    }
    values = list(per_venue.values())
    return FundingDispersion(
        interval_ns=to_interval_ns,
        median_bps=statistics.median(values),
        # Signed extremes, not absolute: a market where two venues pay longs and
        # two pay shorts is wide, and taking absolutes would call it tight.
        spread_bps=max(values) - min(values),
        stdev_bps=statistics.pstdev(values),
        per_venue_bps=per_venue,
        contributors=tuple(sorted(per_venue)),
        excluded=excluded,
    )
