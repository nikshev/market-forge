"""EXP-005: does a boundary sitting on a volume level change the odds?

# @trace: REQ-EXP-005

    Question: does boundary overlap with VAH/VAL/HVN/LVN materially change
    target-before-stop probability?

The one experiment in the set that asks a yes/no question rather than ranking a
list, and the word that needs pinning down is "materially". An effect size
chosen after seeing the answer is not a finding, so it is a required argument
here: a caller must state theirs before the comparison can run.

The answer has three values, and the third is a real one. "Not materially
different" is what most confluence claims turn out to be, and a study that could
only say "higher" or "lower" would say one of them anyway.

The classification is PRD section 14.1's "node overlap with channel boundaries",
which `volume.nodes_at` already answers. This adds the value-area edges, because
EXP-005 names VAH and VAL alongside the nodes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from channelflow.backtest.outcomes import Outcome, SignalOutcome
from channelflow.volume import VolumeProfile, nodes_at

#: How close to a value-area edge counts as touching it, in basis points of the
#: price. A research default: it decides which population a setup joins, and PRD
#: section 13.11's warning about research defaults applies to it.
DEFAULT_BAND_BPS = 10.0

#: Below this, a population cannot support a comparison. Two setups agreeing is
#: not evidence, and a difference computed over them is noise with a decimal
#: point.
DEFAULT_MIN_POPULATION = 20


class Verdict(StrEnum):
    HIGHER = "higher"
    LOWER = "lower"
    #: Not a failure. Most confluence claims land here, and a study that could
    #: not say so would say one of the other two instead.
    NOT_MATERIAL = "not_materially_different"


class PopulationTooSmall(ValueError):
    """One of the two groups cannot support the comparison."""


@dataclass(frozen=True)
class Confluence:
    """Which volume levels a boundary sits on, if any."""

    on_value_area_edge: bool
    node_kind: str | None

    @property
    def present(self) -> bool:
        return self.on_value_area_edge or self.node_kind is not None


@dataclass(frozen=True)
class Observation:
    """One setup: whether its boundary had confluence, and what happened."""

    confluent: bool
    outcome: SignalOutcome


@dataclass(frozen=True)
class Population:
    """One side of the comparison."""

    setups: int
    targets: int
    stops: int
    timeouts: int

    @property
    def decided(self) -> int:
        """Setups that reached a target or a stop -- the ones the probability is over."""
        return self.targets + self.stops

    @property
    def target_before_stop(self) -> float | None:
        """`None` when nothing was decided: a probability over no decisions is not zero."""
        return self.targets / self.decided if self.decided else None


@dataclass(frozen=True)
class ConfluenceResult:
    """The two populations, the difference, and the verdict over it."""

    with_confluence: Population
    without_confluence: Population
    difference: float | None
    effect_size: float
    verdict: Verdict
    excluded_ambiguous: int


def classify(
    boundary: Decimal, profile: VolumeProfile, *, band_bps: float = DEFAULT_BAND_BPS
) -> Confluence:
    """Whether a channel boundary sits on a value-area edge or a volume node."""
    band = abs(boundary) * Decimal(str(band_bps / 10_000.0))
    on_edge = abs(boundary - profile.vah) <= band or abs(boundary - profile.val) <= band
    node = nodes_at(profile, [boundary])[boundary]
    return Confluence(on_value_area_edge=on_edge, node_kind=None if node is None else node.kind)


def confluence_study(
    observations: Sequence[Observation],
    *,
    effect_size: float,
    min_population: int = DEFAULT_MIN_POPULATION,
) -> ConfluenceResult:
    """Compare target-before-stop probability with and without confluence.

    `effect_size` has no default on purpose. "Materially" is the whole question,
    and a threshold chosen after seeing the difference is not a finding about
    the market.
    """
    if effect_size < 0.0:
        raise ValueError("the effect size is a magnitude; a negative one admits everything")

    resolved = [o for o in observations if o.outcome.outcome is not Outcome.AMBIGUOUS]
    excluded = len(observations) - len(resolved)

    with_confluence = _population([o for o in resolved if o.confluent])
    without = _population([o for o in resolved if not o.confluent])

    for name, population in (("with", with_confluence), ("without", without)):
        if population.setups < min_population:
            raise PopulationTooSmall(
                f"the {name}-confluence population has {population.setups} setup(s), "
                f"below {min_population}; a difference computed over them is noise "
                "with a decimal point"
            )

    here, there = with_confluence.target_before_stop, without.target_before_stop
    if here is None or there is None:
        raise PopulationTooSmall(
            "one population decided nothing -- every setup timed out -- so there is "
            "no target-before-stop probability to compare"
        )

    difference = here - there
    if abs(difference) < effect_size:
        verdict = Verdict.NOT_MATERIAL
    else:
        verdict = Verdict.HIGHER if difference > 0 else Verdict.LOWER

    return ConfluenceResult(
        with_confluence=with_confluence,
        without_confluence=without,
        difference=difference,
        effect_size=effect_size,
        verdict=verdict,
        excluded_ambiguous=excluded,
    )


def _population(observations: Sequence[Observation]) -> Population:
    return Population(
        setups=len(observations),
        targets=sum(1 for o in observations if o.outcome.outcome is Outcome.TARGET),
        stops=sum(1 for o in observations if o.outcome.outcome is Outcome.STOP),
        timeouts=sum(1 for o in observations if o.outcome.outcome is Outcome.TIMEOUT),
    )
