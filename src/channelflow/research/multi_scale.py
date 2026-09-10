"""EXP-016: whether nesting a candidate inside a higher timeframe is worth it.

# @trace: REQ-EXP-016

    Evaluate whether nested extrema improve signals: 5m candidate inside 15m
    upper/lower zone; 15m candidate aligned/conflicted with 1h slope;
    directional-change thresholds at multiple scales.

    Measure incremental value, not visual appeal.

The last sentence is the requirement. Multi-scale confluence is the most
visually convincing idea in technical analysis: a chart of the candidates that
survived three timeframes agreeing looks obviously better than a chart of all of
them, because every survivor is a good-looking trade and the ones that were
filtered out are not on the page.

Two numbers say what a chart cannot. **Per trade**, a filter almost always looks
good -- that is what a filter does. **In total**, it can be a loss, because it
also removed the winners. A rule that keeps a twentieth of the candidates and
lifts expectancy by half an R has cost the book nineteen twentieths of its
trades, and no picture shows that.

So every rule here reports both, plus how much it discarded, and the reading
names the case where the two disagree.

The other thing a picture cannot show is *when* the higher timeframe was known.
A 5-minute candidate at 10:07 sits inside a 15-minute bar that closes at 10:15,
and that bar's zone is not available at 10:07. Reading it is the single easiest
look-ahead in this whole experiment and it improves every number: the context
that "confirms" the candidate was partly built out of what happened after it.
Only completed higher-timeframe frames are visible here, and the module refuses
a frame set that has not closed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from channelflow.backtest import CostModel, NothingResolved, SignalOutcome, economic_report
from channelflow.experiments import ConfigValue, Field

#: EXP-016's three nesting rules, in the PRD's order.
RULES: tuple[str, ...] = (
    "inside_higher_zone",
    "aligned_with_higher_slope",
    "confirmed_at_multiple_scales",
)

#: What a rule's two readings can say together.
IMPROVES_BOTH = "improves the average trade and the total"
COSTS_THE_TOTAL = "improves the average trade and loses on the total"
IMPROVES_NEITHER = "improves neither"
UNMEASURED = "not measured"


class UnknownRule(ValueError):
    """A rule outside EXP-016's three."""


class OutOfOrder(ValueError):
    """Higher-timeframe frames did not arrive in closing order."""


@dataclass(frozen=True)
class HigherFrame:
    """One *completed* higher-timeframe bar, and when it became knowable.

    `closed_ns` is the whole point. A frame is context from the moment it closes
    and not one nanosecond before, and the frame a candidate sits inside has not
    closed when the candidate happens.
    """

    closed_ns: int
    zone_low: float
    zone_high: float
    slope: float


@dataclass(frozen=True)
class Candidate:
    """One base-scale extremum candidate and what happened to it."""

    as_of_ns: int
    price: float
    #: "long" at a low, "short" at a high.
    direction: str
    outcome: SignalOutcome

    def __post_init__(self) -> None:
        if self.direction not in ("long", "short"):
            raise ValueError(f"direction {self.direction!r} is neither 'long' nor 'short'")


@dataclass(frozen=True)
class SetEconomics:
    """One set of candidates, priced.

    `total_r` is the number a chart cannot show: expectancy per trade times the
    trades taken. A filter improves the first almost by definition and can halve
    the second.
    """

    trades: int
    expectancy_r: float | None
    total_r: float | None
    win_rate: float | None
    reason: str = ""


@dataclass(frozen=True)
class RuleResult:
    """One nesting rule, against the same candidates without it."""

    rule: str
    base: SetEconomics
    kept: SetEconomics
    #: The candidates the rule rejected. Reported rather than dropped: EXP-016
    #: names "aligned/conflicted" as a pair, and the conflicted set is an arm.
    rejected: SetEconomics
    #: Kept over base. A rule that keeps everything has selected nothing.
    selectivity: float | None
    expectancy_delta: float | None
    total_r_delta: float | None
    reading: str


@dataclass(frozen=True)
class MultiScaleReport:
    """EXP-016's three rules, measured."""

    rules: dict[str, RuleResult]
    candidates: int
    without_context: int
    improvement_floor: float
    configs: dict[str, Mapping[str, ConfigValue]] = field(default_factory=dict)
    note: str = (
        "a filter improves the average trade almost by definition -- that is what a "
        "filter does -- and can lose on the total by removing winners along with "
        "losers. Both numbers are here because a chart of the survivors shows only "
        "the first (PRD EXP-016: measure incremental value, not visual appeal)"
    )

    @property
    def better_looking_than_they_are(self) -> tuple[str, ...]:
        """Rules that lift the average trade and cost the book overall."""
        return tuple(
            name for name, result in self.rules.items() if result.reading == COSTS_THE_TOTAL
        )

    @property
    def compared(self) -> Field:
        """The three nesting rules, and no winner.

        Each rule gets two readings that can disagree -- a filter improves the
        average trade almost by definition and can lose on the total -- and
        EXP-016 names no weighting between them. Picking one here would be this
        module answering a question its own note says it does not answer.
        """
        return Field(variants=self.configs, chosen=None)


def available_frame(frames: Sequence[HigherFrame], as_of_ns: int) -> HigherFrame | None:
    """The last frame that had closed at `as_of_ns`, or nothing.

    `closed_ns <= as_of_ns`, which is the whole guard. The frame a candidate sits
    *inside* has not closed yet, and its zone is partly made of bars that come
    after the candidate. Using it improves every number in this module.
    """
    closings = [frame.closed_ns for frame in frames]
    if closings != sorted(closings):
        raise OutOfOrder(
            "higher-timeframe frames must arrive in closing order; out of order, "
            "'the last frame that had closed' is whichever one happened to be last "
            "in the list"
        )
    latest: HigherFrame | None = None
    for frame in frames:
        if frame.closed_ns > as_of_ns:
            break
        latest = frame
    return latest


def inside_higher_zone(candidate: Candidate, mid: HigherFrame, high: HigherFrame) -> bool:
    """EXP-016's first rule: the candidate's price is inside the mid frame's zone."""
    del high
    return mid.zone_low <= candidate.price <= mid.zone_high


def aligned_with_higher_slope(candidate: Candidate, mid: HigherFrame, high: HigherFrame) -> bool:
    """EXP-016's second: the candidate's direction agrees with the high frame's slope."""
    del mid
    return (candidate.direction == "long" and high.slope > 0.0) or (
        candidate.direction == "short" and high.slope < 0.0
    )


def confirmed_at_multiple_scales(candidate: Candidate, mid: HigherFrame, high: HigherFrame) -> bool:
    """EXP-016's third: both of the above, which is what "multiple scales" means."""
    return inside_higher_zone(candidate, mid, high) and aligned_with_higher_slope(
        candidate, mid, high
    )


_PREDICATES = {
    "inside_higher_zone": inside_higher_zone,
    "aligned_with_higher_slope": aligned_with_higher_slope,
    "confirmed_at_multiple_scales": confirmed_at_multiple_scales,
}


def evaluate_nesting(
    candidates: Sequence[Candidate],
    *,
    mid_frames: Sequence[HigherFrame],
    high_frames: Sequence[HigherFrame],
    costs: CostModel,
    risk_per_trade: float,
    improvement_floor: float,
    rules: Sequence[str] = RULES,
) -> MultiScaleReport:
    """Measure each nesting rule against the same candidates without it.

    `improvement_floor` has no default: it decides what counts as an improvement
    in R, and every reading below moves with it (PRD section 13A.27).

    Candidates with no completed frame on either scale are excluded from every
    arm and counted. Scoring them in the base and not in the filtered arm would
    make the warm-up look like the rule's contribution.
    """
    if improvement_floor <= 0.0:
        raise ValueError(
            "improvement_floor must be positive; a floor of zero calls every "
            "difference an improvement, including the ones that are rounding"
        )
    unknown = [name for name in rules if name not in _PREDICATES]
    if unknown:
        raise UnknownRule(
            f"{', '.join(unknown)} is not one of EXP-016's rules ({', '.join(RULES)})"
        )

    contexts: list[tuple[Candidate, HigherFrame, HigherFrame]] = []
    without_context = 0
    for candidate in candidates:
        mid = available_frame(mid_frames, candidate.as_of_ns)
        high = available_frame(high_frames, candidate.as_of_ns)
        if mid is None or high is None:
            without_context += 1
            continue
        contexts.append((candidate, mid, high))

    base = _price([c for c, _, _ in contexts], costs=costs, risk_per_trade=risk_per_trade)
    results = {
        name: _rule_result(
            name,
            contexts,
            base,
            costs=costs,
            risk_per_trade=risk_per_trade,
            floor=improvement_floor,
        )
        for name in rules
    }
    return MultiScaleReport(
        rules=results,
        candidates=len(candidates),
        without_context=without_context,
        improvement_floor=improvement_floor,
        configs={rule: {"rule": rule, "improvement_floor": improvement_floor} for rule in rules},
    )


EXPERIMENT = "EXP-016"

#: The comparison this module's entry point returns.
COMPARISON = MultiScaleReport


def _rule_result(
    name: str,
    contexts: Sequence[tuple[Candidate, HigherFrame, HigherFrame]],
    base: SetEconomics,
    *,
    costs: CostModel,
    risk_per_trade: float,
    floor: float,
) -> RuleResult:
    predicate = _PREDICATES[name]
    kept = [c for c, mid, high in contexts if predicate(c, mid, high)]
    rejected = [c for c, mid, high in contexts if not predicate(c, mid, high)]
    kept_economics = _price(kept, costs=costs, risk_per_trade=risk_per_trade)
    rejected_economics = _price(rejected, costs=costs, risk_per_trade=risk_per_trade)

    expectancy_delta = _delta(kept_economics.expectancy_r, base.expectancy_r)
    total_delta = _delta(kept_economics.total_r, base.total_r)
    return RuleResult(
        rule=name,
        base=base,
        kept=kept_economics,
        rejected=rejected_economics,
        selectivity=(len(kept) / base.trades if base.trades else None),
        expectancy_delta=expectancy_delta,
        total_r_delta=total_delta,
        reading=_read(expectancy_delta, total_delta, floor),
    )


def _price(
    candidates: Sequence[Candidate], *, costs: CostModel, risk_per_trade: float
) -> SetEconomics:
    """One set of candidates, after costs.

    An empty set has no expectancy and no total. Zero there would let a rule that
    kept nothing rank alongside one that broke even, and only one of those was
    measured.
    """
    if not candidates:
        return SetEconomics(
            trades=0,
            expectancy_r=None,
            total_r=None,
            win_rate=None,
            reason="the rule kept nothing, and expectancy over no trades is not zero",
        )
    try:
        report = economic_report(
            [c.outcome for c in candidates], costs=costs, risk_per_trade=risk_per_trade
        )
    except NothingResolved as exc:
        return SetEconomics(
            trades=0, expectancy_r=None, total_r=None, win_rate=None, reason=str(exc)
        )
    return SetEconomics(
        trades=report.trades,
        expectancy_r=report.expectancy_r,
        # Per trade times trades taken: the number the chart of survivors cannot
        # show, because the trades a filter removed are not on it.
        total_r=report.expectancy_r * report.trades,
        win_rate=report.win_rate,
    )


def _delta(after: float | None, before: float | None) -> float | None:
    """Absent rather than zero when either side was never measured."""
    if after is None or before is None:
        return None
    return after - before


def _read(expectancy_delta: float | None, total_delta: float | None, floor: float) -> str:
    """The two numbers, named.

    `COSTS_THE_TOTAL` is the reading EXP-016's last sentence exists to produce.
    It is also the most common one for a selective rule, and the one a chart of
    the survivors cannot show.
    """
    if expectancy_delta is None or total_delta is None:
        return UNMEASURED
    # The floor guards the per-trade number only. That is the one a filter
    # inflates by construction, so a small positive difference there is what
    # rounding looks like. The total is the book's own outcome over the same
    # candidates: if it went up, it went up, and holding it to a floor measured
    # in per-trade R would be one number meaning two different things.
    better_per_trade = expectancy_delta >= floor
    better_in_total = total_delta > 0.0
    if better_per_trade and better_in_total:
        return IMPROVES_BOTH
    if better_per_trade:
        return COSTS_THE_TOTAL
    return IMPROVES_NEITHER
