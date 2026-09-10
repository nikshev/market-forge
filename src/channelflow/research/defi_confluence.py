"""EXP-015: what derivatives and DeFi context add at a turning point.

# @trace: REQ-EXP-015

    For BTC/ETH and other liquid assets, test whether turning-point probability
    improves from: OI/funding/liquidations; DEX-CEX executable basis; DEX depth
    asymmetry; swap imbalance; LP liquidity migration.

    Use strict ablation and same walk-forward folds.

Two words carry this requirement, and both are checkable rather than assumed.

**Strict** means every arm differs from its reference by exactly one family. An
ablation whose arms differ in two things reports the sum of two contributions
under one name, and the sum is not attributable to either. So the arms come in
two families of their own -- each candidate added to the baseline alone, and
each candidate removed from the full set -- and the module refuses a set of arms
that is not strict rather than scoring it.

The two directions answer different questions and routinely disagree. A family
that helps on its own and adds nothing to the full set is redundant with
something already there; a family that adds nothing alone and helps in context
only works alongside another. Reporting one number would hide whichever case the
data is in.

**Same walk-forward folds** means one certified dataset, used as given, for
every arm. The failure it guards against is not subtle and is easy to commit: a
per-family study run separately and the numbers put in one table. Each report
carries the fingerprint of the folds it ran on, and comparing two reports across
different folds is refused.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from channelflow.dataset import CertifiedDataset
from channelflow.experiments import Field
from channelflow.research.ablation import AblationArm, AblationReport, ArmEntry, run_ablation
from channelflow.research.cumulative import Increment, resolve_membership
from channelflow.turning.direct import Target

#: The baseline every candidate is measured against: the channel state alone.
BASELINE_FAMILY = "channel"

#: EXP-015's five candidates, in the PRD's order.
CANDIDATE_FAMILIES: tuple[str, ...] = (
    "oi_funding_liquidations",
    "dex_cex_basis",
    "dex_depth_asymmetry",
    "swap_imbalance",
    "lp_migration",
)

#: The taxonomy the arms are checked against.
FAMILIES: tuple[str, ...] = (BASELINE_FAMILY, *CANDIDATE_FAMILIES)

#: How each family is found in the registry, by name prefix. Prefixes rather
#: than hand-kept lists, so a feature added to a producing module joins the
#: family it belongs to without anybody remembering to add it here.
_MEMBERSHIP: dict[str, tuple[str, ...]] = {
    "channel": ("channel_",),
    "oi_funding_liquidations": (
        "oi_",
        "open_interest_",
        "funding_",
        "liquidation_",
        "price_oi_regime",
        "time_since_liquidation_spike",
    ),
    # Not `basis_`: the registry's `basis_bps` is PRD section 16's perp-spot
    # basis, a CEX derivatives feature. Matching it here would put a CEX number
    # in the DEX arm and report its contribution as the DEX view's. The same
    # trap [[ADR-046]]'s experiment walked into.
    "dex_cex_basis": ("dex_divergence_",),
    "dex_depth_asymmetry": ("dex_depth_asymmetry",),
    "swap_imbalance": ("dex_swap_imbalance",),
    "lp_migration": ("dex_lp_",),
}

#: The name of the arm holding every family.
FULL_ARM = "all_families"

#: What a family's pair of readings can say.
ADDS_BOTH_WAYS = "adds alone and in context"
REDUNDANT = "adds alone but nothing to the full set"
ONLY_IN_CONTEXT = "adds nothing alone but helps the full set"
ADDS_NOTHING = "adds nothing either way"
UNMEASURED = "not measured"


class NotStrict(ValueError):
    """An arm differs from its reference by more than one family."""


class DifferentFolds(ValueError):
    """Two reports were scored on different walk-forward folds."""


class InstrumentsMissing(ValueError):
    """The dataset does not carry the instruments the report claims."""


@dataclass(frozen=True)
class FoldFingerprint:
    """Enough of a fold set to tell two of them apart.

    Not the folds themselves: a fingerprint is what a *report* can carry, and
    the point is to make "the same folds" a claim a reader can check rather than
    a sentence in a method section.
    """

    folds: int
    spans: tuple[tuple[int, int, int, int], ...]


@dataclass(frozen=True)
class FamilyValue:
    """One candidate family, measured both ways."""

    family: str
    #: Added to the baseline on its own.
    alone: Increment | None
    #: Removed from the full set. A negative delta here means the full set got
    #: *worse* without the family, which is the family adding value.
    in_context: Increment | None
    reading: str


@dataclass(frozen=True)
class ConfluenceReport:
    """EXP-015's ablation, read family by family."""

    ablation: AblationReport
    families: dict[str, FamilyValue]
    fingerprint: FoldFingerprint
    instruments: tuple[str, ...]
    improvement_floor: float

    @property
    def redundant(self) -> tuple[str, ...]:
        """Families that help alone and add nothing to the full set."""
        return tuple(name for name, value in self.families.items() if value.reading == REDUNDANT)

    @property
    def compared(self) -> Field:
        """The strict arms this confluence study ablated."""
        return self.ablation.compared


EXPERIMENT = "EXP-015"

#: The comparison this module's entry point returns.
COMPARISON = ConfluenceReport


def strict_arms(candidates: Sequence[str] = CANDIDATE_FAMILIES) -> tuple[AblationArm, ...]:
    """The baseline, each candidate added alone, the full set, each removed.

    Every arm is one family away from either the baseline or the full set. That
    is what makes each difference attributable to the family it names.
    """
    full = (BASELINE_FAMILY, *candidates)
    arms = [AblationArm(name="baseline", families=(BASELINE_FAMILY,), taxonomy=FAMILIES)]
    arms.extend(
        AblationArm(name=f"plus_{family}", families=(BASELINE_FAMILY, family), taxonomy=FAMILIES)
        for family in candidates
    )
    arms.append(AblationArm(name=FULL_ARM, families=full, taxonomy=FAMILIES))
    arms.extend(
        AblationArm(
            name=f"minus_{family}",
            families=tuple(f for f in full if f != family),
            taxonomy=FAMILIES,
        )
        for family in candidates
    )
    return tuple(arms)


def strictness_violations(arms: Sequence[AblationArm]) -> tuple[str, ...]:
    """Arms that are not one family away from the baseline or the full set.

    Public because "strict" is EXP-015's own word and a property nobody can
    check by reading a table of numbers. An arm two families from both
    references still produces a delta, and the delta still looks like one
    family's contribution.
    """
    by_name = {arm.name: frozenset(arm.families) for arm in arms}
    baseline = by_name.get("baseline")
    full = by_name.get(FULL_ARM)
    if baseline is None or full is None:
        return ("baseline" if baseline is None else FULL_ARM,)

    violations: list[str] = []
    for arm in arms:
        families = by_name[arm.name]
        if families in (baseline, full):
            continue
        if len(families ^ baseline) == 1 or len(families ^ full) == 1:
            continue
        violations.append(arm.name)
    return tuple(violations)


def available_from_registry() -> dict[str, tuple[str, ...]]:
    """Which registered features belong to each of EXP-015's families."""
    return resolve_membership(_MEMBERSHIP)


def fingerprint(dataset: CertifiedDataset) -> FoldFingerprint:
    """The shape and edges of a fold set, enough to tell two apart."""
    spans = tuple(
        (
            fold.index,
            len(fold.train),
            len(fold.validate),
            fold.validate[-1].as_of_ns if fold.validate else -1,
        )
        for fold in dataset.folds
    )
    return FoldFingerprint(folds=len(dataset.folds), spans=spans)


def require_same_folds(reports: Sequence[ConfluenceReport]) -> None:
    """Refuse a comparison across reports that did not share their folds.

    The failure this exists for is a per-family study run separately and the
    numbers put in one table. Nothing about those numbers looks wrong.
    """
    prints = {report.fingerprint for report in reports}
    if len(prints) > 1:
        raise DifferentFolds(
            f"{len(reports)} report(s) carry {len(prints)} different fold sets; a "
            "difference between arms scored on different splits is the difference "
            "between the splits as much as between the arms"
        )


def run_confluence_ablation(
    dataset: CertifiedDataset,
    *,
    target: Target,
    instruments: Sequence[str],
    improvement_floor: float,
    available: Mapping[str, Sequence[str]] | None = None,
    arms: Sequence[AblationArm] | None = None,
) -> ConfluenceReport:
    """Run EXP-015's strict ablation on one fold set.

    `instruments` has no default. EXP-015 names BTC and ETH "and other liquid
    assets", and a pooled result read as a single asset's is a different claim
    from the one the numbers support -- so the report says which assets it
    covered, and refuses to name one the dataset does not contain.

    `improvement_floor` has no default either. It decides what counts as an
    improvement, and every reading below moves with it (PRD section 13A.27).
    """
    if improvement_floor <= 0.0:
        raise ValueError(
            "improvement_floor must be positive; a floor of zero calls every "
            "difference an improvement, including the ones that are rounding"
        )
    if not instruments:
        raise InstrumentsMissing(
            "EXP-015 is about named liquid assets; a report that does not say which "
            "is a result about nothing in particular"
        )

    entities = {row.entity for fold in dataset.folds for row in fold.validate}
    absent = [name for name in instruments if name not in entities]
    if absent:
        raise InstrumentsMissing(
            f"the dataset carries no rows for {', '.join(absent)}; a report naming an "
            f"asset it never scored is a claim about that asset. Present: "
            f"{', '.join(sorted(entities))}"
        )

    chosen = tuple(arms) if arms is not None else strict_arms()
    violations = strictness_violations(chosen)
    if violations:
        raise NotStrict(
            f"{', '.join(violations)} differ from both the baseline and the full set by "
            "more than one family; the delta would be the sum of several contributions "
            "reported under one family's name"
        )

    resolved = dict(available) if available is not None else available_from_registry()
    ablation = run_ablation(dataset, target=target, available=resolved, arms=chosen)
    entries = {entry.arm: entry for entry in ablation.entries}

    families = {
        family: _value(family, entries, resolved, improvement_floor)
        for family in CANDIDATE_FAMILIES
    }
    return ConfluenceReport(
        ablation=ablation,
        families=families,
        fingerprint=fingerprint(dataset),
        instruments=tuple(instruments),
        improvement_floor=improvement_floor,
    )


def _value(
    family: str,
    entries: Mapping[str, ArmEntry],
    available: Mapping[str, Sequence[str]],
    floor: float,
) -> FamilyValue:
    alone = _delta(entries, after=f"plus_{family}", before="baseline", available=available)
    # Removing the family: the delta is the full set *minus* the family against
    # the full set, so a positive number means the set got worse without it --
    # which is the family adding value. Taken in this direction so both readings
    # share a sign convention with `alone`, where negative is an improvement.
    removed = _delta(entries, after=f"minus_{family}", before=FULL_ARM, available=available)
    in_context = (
        None
        if removed is None or removed.brier_delta is None
        else Increment(
            arm=FULL_ARM,
            over=f"minus_{family}",
            added_features=removed.added_features,
            brier_delta=-removed.brier_delta,
        )
    )
    return FamilyValue(
        family=family,
        alone=alone,
        in_context=in_context,
        reading=_read(alone, in_context, floor),
    )


def _delta(
    entries: Mapping[str, ArmEntry],
    *,
    after: str,
    before: str,
    available: Mapping[str, Sequence[str]],
) -> Increment | None:
    """One arm against another, or nothing when either did not run.

    Absent rather than zero: "this family added nothing" and "there was nothing
    to add it to" are different findings, and a zero reports the second as the
    first.
    """
    first, second = entries.get(before), entries.get(after)
    if first is None or second is None:
        return None
    added = tuple(name for name in second.features if name not in first.features)
    if (
        first.result is None
        or second.result is None
        or first.result.model_brier is None
        or second.result.model_brier is None
    ):
        return Increment(
            arm=after,
            over=before,
            added_features=added,
            brier_delta=None,
            note=(
                f"{after if second.result is None else before} was not scored, so there "
                "is no difference to take"
            ),
        )
    return Increment(
        arm=after,
        over=before,
        added_features=added,
        brier_delta=second.result.model_brier - first.result.model_brier,
    )


def _read(alone: Increment | None, in_context: Increment | None, floor: float) -> str:
    """The two directions, named.

    `REDUNDANT` is the reading a single-direction ablation cannot produce: a
    family that improves on the baseline and adds nothing to the full set is
    carrying information something else already carries.
    """
    if alone is None or in_context is None:
        return UNMEASURED
    if alone.brier_delta is None or in_context.brier_delta is None:
        return UNMEASURED
    # Lower Brier is better, so an improvement is a delta below the negated floor.
    helps_alone = alone.brier_delta <= -floor
    helps_in_context = in_context.brier_delta <= -floor
    if helps_alone and helps_in_context:
        return ADDS_BOTH_WAYS
    if helps_alone:
        return REDUNDANT
    if helps_in_context:
        return ONLY_IN_CONTEXT
    return ADDS_NOTHING
