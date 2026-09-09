"""Cumulative ablations, and the increments between their arms.

# @trace: REQ-EXP-004
# @trace: REQ-EXP-007

Two experiments ask the same question of different families -- EXP-004 of the
order book, EXP-007 of the DEX -- and both ask it the same way: arms that each
contain the previous one and add exactly one family, so the difference between
neighbours is that family's contribution and nothing else.

The shape lives here and the taxonomies live with their experiments. A second
copy of this arithmetic would drift, and the two experiments' numbers would stop
meaning the same thing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from channelflow.dataset import CertifiedDataset
from channelflow.features import exposed_feature_names
from channelflow.features.registry import REGISTRY
from channelflow.research.ablation import AblationArm, AblationReport, run_ablation
from channelflow.turning.direct import Target


@dataclass(frozen=True)
class Increment:
    """What one family added over the arm before it."""

    arm: str
    over: str
    added_features: tuple[str, ...]
    #: Lower Brier is better, so a negative delta is an improvement. `None` when
    #: either arm did not run -- an increment over an arm that was never scored
    #: is not zero.
    brier_delta: float | None
    note: str = ""


@dataclass(frozen=True)
class IncrementalReport:
    """The ablation, and the increments read off it."""

    ablation: AblationReport
    increments: tuple[Increment, ...]


def resolve_membership(
    membership: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    """Which registered features belong to each family, by name prefix.

    Read from `REGISTRY` rather than listed by hand, so an arm cannot claim a
    feature that does not exist and cannot miss one that does.

    `exposed_feature_names` is called first for its import side effect: a
    registry entry appears when its producing module is imported, so reading
    `REGISTRY` cold sees only whatever happened to be loaded already -- which
    made every order-flow family look empty the first time this ran.
    """
    exposed_feature_names()
    return {
        family: tuple(sorted(name for name in REGISTRY if name.startswith(tuple(prefixes))))
        for family, prefixes in membership.items()
    }


def run_cumulative_ablation(
    dataset: CertifiedDataset,
    *,
    target: Target,
    available: Mapping[str, Sequence[str]],
    arms: Sequence[AblationArm],
) -> IncrementalReport:
    """Score the arms and report what each family added over the one before."""
    ablation = run_ablation(dataset, target=target, available=available, arms=arms)
    return IncrementalReport(ablation=ablation, increments=increments_of(ablation, arms, available))


def increments_of(
    report: AblationReport,
    arms: Sequence[AblationArm],
    available: Mapping[str, Sequence[str]],
) -> tuple[Increment, ...]:
    """Each arm against the one before it.

    The absolute scores are in the ablation; these are the differences, which is
    what "incremental value" names. An increment over an arm that did not run is
    absent rather than zero: "this family added nothing" and "there was nothing
    to add it to" are different findings.
    """
    entries = {entry.arm: entry for entry in report.entries}
    increments: list[Increment] = []
    for previous, arm in zip(arms, arms[1:], strict=False):
        before, after = entries.get(previous.name), entries.get(arm.name)
        added = tuple(
            name for name in arm.resolve(available) if name not in previous.resolve(available)
        )
        if (
            before is None
            or after is None
            or before.result is None
            or after.result is None
            or before.result.model_brier is None
            or after.result.model_brier is None
        ):
            increments.append(
                Increment(
                    arm=arm.name,
                    over=previous.name,
                    added_features=added,
                    brier_delta=None,
                    note="one of the two arms was not scored, so there is no difference to take",
                )
            )
            continue
        increments.append(
            Increment(
                arm=arm.name,
                over=previous.name,
                added_features=added,
                brier_delta=after.result.model_brier - before.result.model_brier,
            )
        )
    return tuple(increments)
