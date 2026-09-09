"""An ablation across feature families (PRD section 25.6).

# @trace: REQ-US-006
# @trace: REQ-US-007

REQ-US-006 names five arms: channel only; channel + order flow; channel +
derivatives; channel + DEX; all combined. EXP-015 adds the condition that makes
them comparable -- "use strict ablation and same walk-forward folds" -- so every
arm is scored on one fold set, built once by the caller.

The load-bearing part is what the report refuses to say. The feature registry
carries order-flow and derivatives features today and no DEX ones, so "channel +
DEX" resolves to the same features as "channel only". Scored and reported, it
would produce an identical number, and a reader would take that as evidence that
the DEX family adds nothing -- a finding about the data pipeline wearing the
clothes of a finding about the market.

So an arm that resolves to nothing, or to a set an earlier arm already used, is
reported as not run with the reason. It does not enter the ranking. The same
distinction [[ADR-044]] makes in the score: what the system could not look at is
never reported as what it looked at and found.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from channelflow.dataset import CertifiedDataset
from channelflow.turning.direct import DirectBaselineResult, Target, run_direct_baseline

#: REQ-US-006's groups, mapped onto the feature registry's own family names.
#: `channel` and `dex` have no registered features yet, which is why an arm can
#: be unrunnable at all.
FAMILIES: tuple[str, ...] = ("channel", "order_flow", "derivatives", "dex")


class UnknownFamily(ValueError):
    """An arm names a family the taxonomy does not know."""


@dataclass(frozen=True)
class AblationArm:
    """One feature set under test."""

    name: str
    families: tuple[str, ...]

    def __post_init__(self) -> None:
        unknown = [f for f in self.families if f not in FAMILIES]
        if unknown:
            raise UnknownFamily(
                f"arm {self.name!r} names {', '.join(unknown)}, which the taxonomy does "
                f"not know ({', '.join(FAMILIES)}); an unknown family resolves to no "
                "features, which is indistinguishable from missing data -- and one of "
                "those is a typo"
            )

    def resolve(self, available: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
        """The feature names this arm actually has, in a stable order."""
        names: list[str] = []
        for family in self.families:
            names.extend(available.get(family, ()))
        return tuple(sorted(set(names)))


#: REQ-US-006's five, in its own order.
ARMS: tuple[AblationArm, ...] = (
    AblationArm(name="channel_only", families=("channel",)),
    AblationArm(name="channel_order_flow", families=("channel", "order_flow")),
    AblationArm(name="channel_derivatives", families=("channel", "derivatives")),
    AblationArm(name="channel_dex", families=("channel", "dex")),
    AblationArm(name="all_combined", families=FAMILIES),
)


@dataclass(frozen=True)
class ArmEntry:
    """What happened to one arm."""

    arm: str
    features: tuple[str, ...]
    #: `None` when the arm was not run. The reason says which case it was.
    result: DirectBaselineResult | None
    reason: str = ""


@dataclass(frozen=True)
class AblationReport:
    """Every arm, the ranking over those that ran, and the folds they shared."""

    entries: tuple[ArmEntry, ...]
    ranking: tuple[str, ...]
    folds: int
    target: str

    @property
    def runnable(self) -> bool:
        return bool(self.ranking)

    @property
    def summary(self) -> str:
        if not self.runnable:
            unrun = "; ".join(f"{e.arm}: {e.reason}" for e in self.entries if e.result is None)
            return f"no arm could be run over {self.folds} fold(s): {unrun}"
        best = self.ranking[0]
        return (
            f"{len(self.ranking)} of {len(self.entries)} arm(s) ran over {self.folds} "
            f"fold(s); {best} scored best"
        )


def run_ablation(
    dataset: CertifiedDataset,
    *,
    target: Target,
    available: Mapping[str, Sequence[str]],
    arms: Sequence[AblationArm] = ARMS,
) -> AblationReport:
    """Score every arm on one fold set.

    The folds come from the certificate and are used as given. Rebuilding them
    per arm would make each arm's score depend on its own split, and the
    difference between two arms would no longer be the families under test.

    A `CertifiedDataset` because this fits models (REQ-US-007).
    """
    entries: list[ArmEntry] = []
    seen: dict[tuple[str, ...], str] = {}

    for arm in arms:
        features = arm.resolve(available)
        # A family that contributed nothing is the reason, checked before the
        # duplicate test: "channel + DEX" over rows with no DEX features
        # resolves to the channel's own features, so the duplicate branch would
        # report it as a repeat of "channel only" and bury the cause.
        missing = [f for f in arm.families if not available.get(f)]
        if missing:
            entries.append(
                ArmEntry(
                    arm=arm.name,
                    features=features,
                    result=None,
                    reason=(
                        f"no features available for {', '.join(missing)}; scoring it would "
                        "report the absence of data as the absence of value"
                    ),
                )
            )
            continue
        if features in seen:
            entries.append(
                ArmEntry(
                    arm=arm.name,
                    features=features,
                    result=None,
                    reason=(
                        f"resolves to the same features as {seen[features]}; one "
                        "measurement reported twice is not a comparison"
                    ),
                )
            )
            continue

        seen[features] = arm.name
        entries.append(
            ArmEntry(
                arm=arm.name,
                features=features,
                # The same scoring path REQ-WP-019's direct target uses. A second
                # one here would make the arms comparable only to each other.
                result=run_direct_baseline(dataset, target=target, feature_names=features),
            )
        )

    return AblationReport(
        entries=tuple(entries),
        ranking=rank_arms(entries),
        folds=len(dataset.folds),
        target=str(target),
    )


def rank_arms(entries: Sequence[ArmEntry]) -> tuple[str, ...]:
    """Best score first, ties broken by name.

    Public because the tie-break is the part that can be wrong and the part a
    real ablation rarely exercises: two arms over different features almost
    never score identically, so a ranking that depended on entry order would
    agree with itself on every realistic input.
    """
    scored = [e for e in entries if e.result is not None and e.result.model_brier is not None]
    return tuple(
        e.arm
        # Lower Brier is better; the name breaks ties so one input gives one
        # ordering.
        for e in sorted(scored, key=lambda e: (e.result.model_brier if e.result else 0.0, e.arm))
    )
