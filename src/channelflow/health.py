"""PRD section 32's data-quality layer.

# @trace: REQ-WP-035

Section 32 gives four states and, directly beneath them, eligibility rules that
treat them differently -- a degraded confirmation lowers confidence, a stale
book disqualifies a signal outright. Four states rather than a boolean is
therefore not fastidiousness: "unhealthy" makes the rules above unimplementable
while looking like a simplification.

**An absent reading is not a reading within its limit.** This is the sharpest
form of "absent is not zero" in the whole document, because the failure it
guards against -- a feed gone so wrong it cannot report at all -- is exactly the
failure this layer exists to catch, and a default of GOOD is precisely what
silences it. The silence then looks identical to a healthy system.

Section 32 lists nine metrics and no values, which is section 13.11's situation:
every threshold here is an argument, and a constant would be a research default
wearing a decision's clothes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class HealthState(IntEnum):
    """Section 32's four, ranked so the worst decides by comparison.

    An `IntEnum` rather than a `StrEnum` because "the worst reading decides" is
    then one `max`, not a conditional chain that a tenth metric would have to be
    threaded through. The ordering has its own test: mis-ordered, a stale feed
    outranks an invalid one and every assessment still returns a plausible
    state -- a defect with no symptom.
    """

    GOOD = 0
    DEGRADED = 1
    STALE = 2
    INVALID = 3


@dataclass(frozen=True)
class HealthReadings:
    """What a feed reported. `None` means **not reported**, never "fine"."""

    reconnects: int | None = None
    missing_bars: int | None = None
    stale_ns: int | None = None
    gap_rate: float | None = None
    duplicate_rate: float | None = None


@dataclass(frozen=True)
class HealthThresholds:
    """Where each metric stops being acceptable.

    Defaults are stated so a caller has somewhere to start, and they are
    defaults rather than findings -- section 13.11 calls numbers like these
    research defaults, not proven parameters.
    """

    reconnects: int = 2
    missing_bars: int = 0
    stale_ns: int = 5 * 1_000_000_000
    gap_rate: float = 0.0
    duplicate_rate: float = 0.01


@dataclass(frozen=True)
class FeedHealth:
    """What one feed is currently worth, and why."""

    feed: str
    state: HealthState
    reason: str
    observed_at_ns: int


#: Which metric produces which state when it is over its limit. Reconnects and
#: missing bars degrade; a stale clock is its own state; gaps and duplicates
#: mean the stream cannot be trusted at all.
#:
#: In section 32's own order, which is deliberately not sorted by severity. A
#: list that happened to run mildest-first would make "the worst decides"
#: indistinguishable from "the last one decides" -- the mutation sweep found
#: exactly that, and the guard was unreachable until this order made it matter.
_RULES: tuple[tuple[str, HealthState, str], ...] = (
    ("reconnects", HealthState.DEGRADED, "reconnect count"),
    ("gap_rate", HealthState.INVALID, "sequence gap rate"),
    ("stale_ns", HealthState.STALE, "stale seconds"),
    ("missing_bars", HealthState.DEGRADED, "missing bars"),
    ("duplicate_rate", HealthState.INVALID, "duplicate rate"),
)


def assess(
    readings: HealthReadings,
    *,
    feed: str,
    at_ns: int,
    thresholds: HealthThresholds,
) -> FeedHealth:
    """What a feed is worth, given what it said and what it did not say.

    A metric it did not report is counted against it, not for it. A feed
    reporting only its easiest metric must not read like one reporting all of
    them, and a feed reporting nothing at all must not read like a quiet market.
    """
    silent = [name for name, _, _ in _RULES if getattr(readings, name) is None]
    if len(silent) == len(_RULES):
        return FeedHealth(
            feed=feed,
            state=HealthState.INVALID,
            # INVALID rather than a fifth state: section 32's eligibility rules
            # name four, and an `UNKNOWN` would need a rule in each of them that
            # the PRD never gives. The reason carries what the state name only
            # approximates -- invalid because gappy against invalid because
            # silent.
            reason="nothing was reported: the feed said neither good news nor bad",
            observed_at_ns=at_ns,
        )

    worst = HealthState.GOOD
    blamed = "every reading within its limit"
    for name, state, label in _RULES:
        value = getattr(readings, name)
        if value is None:
            # Not reported. Held against the feed at the state the metric would
            # have produced, because an unreported metric is exactly as
            # informative as a bad one about whether to trust this feed.
            candidate, why = state, f"{label} was not reported"
        elif value > getattr(thresholds, name):
            candidate, why = state, f"{label} is over its limit at {value}"
        else:
            continue
        if candidate > worst:
            worst, blamed = candidate, why

    return FeedHealth(feed=feed, state=worst, reason=blamed, observed_at_ns=at_ns)
