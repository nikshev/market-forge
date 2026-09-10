"""EXP-006: what the derivatives state says about how a setup ends.

# @trace: REQ-EXP-006

    Analyze conditional outcomes by: funding z-score; OI change; liquidation
    imbalance; basis.

A conditional study, and EXP-014 names the trap it shares with every other one:
"repeat point-in-time as a predictive experiment to avoid confusing
contemporaneous explanation with forecast value". A conditional computed on the
state *at* signal time is predictive; one computed on the state *around* the
outcome explains it. Both are useful and only one is tradeable, so every result
here carries which it is, and the caller says so rather than the module
guessing.

Each variable is bucketed by declared edges. Quantiles computed from the sample
would move with it -- two runs over different windows would bucket the same
funding reading differently and their conditionals could not be compared.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from channelflow.backtest import CostModel, CostsRequired, EconomicReport, economic_report
from channelflow.backtest.outcomes import Outcome, SignalOutcome
from channelflow.experiments import ConfigValue, Field

#: EXP-006's four, by their registered feature names.
VARIABLES: tuple[str, ...] = (
    "funding_z",
    "oi_change_5m",
    "liquidation_imbalance_5m",
    "basis_bps",
)

#: Declared edges per variable, not quantiles of the sample. Research defaults:
#: they decide which bucket a reading joins, and PRD section 13.11's warning
#: applies to them. A z-score of two is the usual "unusual"; the others are
#: round numbers chosen to be visible rather than tuned.
DEFAULT_EDGES: dict[str, tuple[float, ...]] = {
    "funding_z": (-2.0, 0.0, 2.0),
    "oi_change_5m": (-0.02, 0.0, 0.02),
    "liquidation_imbalance_5m": (-0.5, 0.0, 0.5),
    "basis_bps": (-10.0, 0.0, 10.0),
}

#: A bucket smaller than this is reported with its count and not scored. A
#: conditional over three setups is noise with a label on it.
DEFAULT_MIN_BUCKET = 10


@dataclass(frozen=True)
class Observation:
    """One setup: the derivatives state it was seen in, and what happened."""

    values: dict[str, float]
    outcome: SignalOutcome


@dataclass(frozen=True)
class Bucket:
    """One band of one variable, and the outcomes that fell in it."""

    label: str
    low: float | None
    high: float | None
    setups: int
    #: `None` when the bucket was too small to score, or nothing resolved in it.
    report: EconomicReport | None = None
    reason: str = ""


@dataclass(frozen=True)
class VariableConditional:
    """One variable's buckets, or why it has none."""

    variable: str
    buckets: tuple[Bucket, ...] = ()
    edges: tuple[float, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class ConditionalReport:
    """Every variable, and what the whole study is a study of."""

    conditionals: dict[str, VariableConditional]
    costs: CostModel
    #: True when the values were read at signal time, false when they were read
    #: around the outcome. EXP-014's distinction, carried rather than assumed.
    point_in_time: bool
    excluded_ambiguous: int
    configs: dict[str, Mapping[str, ConfigValue]] = field(default_factory=dict)
    note: str = field(default="")

    def __post_init__(self) -> None:
        if not self.note:
            label = (
                "point-in-time: the state was read at signal time, so these "
                "conditionals are predictive"
                if self.point_in_time
                else "contemporaneous: the state was read around the outcome, so these "
                "conditionals explain rather than forecast (EXP-014)"
            )
            object.__setattr__(self, "note", label)

    @property
    def compared(self) -> Field:
        """The variables this study conditioned on, and no winner.

        A conditional study ranks nothing -- but the variables are a field in
        PRD §41 rule 11's sense all the same. Someone quoting the one that
        looked good needs the other three on record, which is the whole of what
        the rule asks for.

        `point_in_time` is in every variant's config because it changes what the
        number means: the same variable computed around the outcome explains it
        and computed at signal time predicts it, and recording both under one
        identity would merge an explanation with a forecast.
        """
        return Field(variants=self.configs, chosen=None)


def conditional_study(
    observations: Sequence[Observation],
    *,
    costs: CostModel | None,
    point_in_time: bool,
    variables: Sequence[str] = VARIABLES,
    edges: Mapping[str, Sequence[float]] | None = None,
    min_bucket: int = DEFAULT_MIN_BUCKET,
    risk_per_trade: float = 0.02,
) -> ConditionalReport:
    """Outcomes by derivatives state, one variable at a time.

    `point_in_time` has no default. It decides whether the answer is a forecast
    or an explanation, and a module that guessed would label somebody else's
    study.
    """
    if costs is None:
        raise CostsRequired(
            "the conditionals are economic, and PRD section 41 rule 9 governs them "
            "wherever they are computed"
        )

    resolved = [o for o in observations if o.outcome.outcome is not Outcome.AMBIGUOUS]
    excluded = len(observations) - len(resolved)
    chosen_edges = {**DEFAULT_EDGES, **(dict(edges) if edges else {})}

    conditionals: dict[str, VariableConditional] = {}
    for variable in variables:
        present = [o for o in resolved if variable in o.values]
        if not present:
            # Not a flat conditional. "No data" and "no relationship" look
            # identical once both are rendered as one bucket of everything.
            conditionals[variable] = VariableConditional(
                variable=variable,
                reason=f"no observation carried {variable!r}; a variable with no data is "
                "not a variable with no effect",
            )
            continue
        conditionals[variable] = VariableConditional(
            variable=variable,
            edges=tuple(chosen_edges.get(variable, ())),
            buckets=_buckets(
                present,
                variable,
                tuple(chosen_edges.get(variable, ())),
                costs=costs,
                min_bucket=min_bucket,
                risk_per_trade=risk_per_trade,
            ),
        )

    return ConditionalReport(
        conditionals=conditionals,
        costs=costs,
        point_in_time=point_in_time,
        excluded_ambiguous=excluded,
        configs={name: {"variable": name, "point_in_time": point_in_time} for name in variables},
    )


EXPERIMENT = "EXP-006"

#: The comparison this module's entry point returns.
COMPARISON = ConditionalReport


def _buckets(
    observations: Sequence[Observation],
    variable: str,
    edges: Sequence[float],
    *,
    costs: CostModel,
    min_bucket: int,
    risk_per_trade: float,
) -> tuple[Bucket, ...]:
    """Split by the declared edges, and score what is big enough to score."""
    bounds = [None, *edges, None]
    built: list[Bucket] = []
    for low, high in zip(bounds, bounds[1:], strict=False):
        inside = [
            o
            for o in observations
            if (low is None or o.values[variable] >= low)
            and (high is None or o.values[variable] < high)
        ]
        label = f"{'-inf' if low is None else low} to {'inf' if high is None else high}"
        if len(inside) < min_bucket:
            built.append(
                Bucket(
                    label=label,
                    low=low,
                    high=high,
                    setups=len(inside),
                    reason=f"{len(inside)} setup(s), below the minimum of {min_bucket}",
                )
            )
            continue
        try:
            report = economic_report(
                [o.outcome for o in inside], costs=costs, risk_per_trade=risk_per_trade
            )
        except ValueError as exc:
            built.append(
                Bucket(label=label, low=low, high=high, setups=len(inside), reason=str(exc))
            )
            continue
        built.append(Bucket(label=label, low=low, high=high, setups=len(inside), report=report))
    return tuple(built)
