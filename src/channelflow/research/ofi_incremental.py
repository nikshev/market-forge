"""EXP-004: what each order-flow family adds over the channel alone.

# @trace: REQ-EXP-004

    Ablation: channel only; +L1 imbalance; +multi-level imbalance; +OFI;
    +persistence/cancellation.

Cumulative, in the PRD's own order: each arm contains the previous arm's
features and adds one family. That is what makes the differences readable as
increments -- arms that differed in more than the family under test would report
the sum of every difference between them.

The taxonomy slices the feature registry more finely than [[REQ-US-006]]'s four
groups do, because EXP-004's question is inside what that experiment calls
"order flow": L1 imbalance, the multi-level book, OFI itself, and wall
persistence are four different claims about the same book.

The scoring is REQ-US-006's ablation, unchanged. This module supplies the arms,
the taxonomy and the increments; a second scoring path would make EXP-004's
numbers incomparable with every other experiment's.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from channelflow.dataset import CertifiedDataset
from channelflow.features import REGISTRY, exposed_feature_names
from channelflow.research.ablation import AblationArm, AblationReport, run_ablation
from channelflow.turning.direct import Target

#: EXP-004's families, finer than REQ-US-006's four. Every name here is a family
#: in the feature registry or a prefix within one; `available_from_registry`
#: resolves them to feature names so the arms cannot drift from what exists.
FAMILIES: tuple[str, ...] = (
    "channel",
    "l1_imbalance",
    "multi_level_imbalance",
    "ofi",
    "persistence_cancellation",
)

#: How each family is found in the registry. Prefixes rather than a hand-kept
#: list: a feature added to the book module joins the arm it belongs to without
#: anybody remembering to add it here.
_MEMBERSHIP: dict[str, tuple[str, ...]] = {
    "channel": ("channel_",),
    "l1_imbalance": ("qi_l1", "microprice"),
    "multi_level_imbalance": ("depth_imbalance_",),
    "ofi": ("ofi_",),
    "persistence_cancellation": ("wall_",),
}

#: The five arms, cumulative in EXP-004's order.
ARMS: tuple[AblationArm, ...] = tuple(
    AblationArm(name=name, families=FAMILIES[: index + 1], taxonomy=FAMILIES)
    for index, name in enumerate(
        (
            "channel_only",
            "plus_l1_imbalance",
            "plus_multi_level_imbalance",
            "plus_ofi",
            "plus_persistence_cancellation",
        )
    )
)


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


def available_from_registry() -> dict[str, tuple[str, ...]]:
    """Which registered features belong to each of EXP-004's families.

    Read from `REGISTRY` rather than listed here, so an arm cannot claim a
    feature that does not exist and cannot miss one that does.

    `exposed_feature_names` is called first for its import side effect: a
    registry entry appears when its producing module is imported, so reading
    `REGISTRY` cold sees only whatever happened to be loaded already -- which
    made every order-flow arm look empty.
    """
    exposed_feature_names()
    found: dict[str, tuple[str, ...]] = {}
    for family, prefixes in _MEMBERSHIP.items():
        found[family] = tuple(sorted(name for name in REGISTRY if name.startswith(prefixes)))
    return found


def run_ofi_ablation(
    dataset: CertifiedDataset,
    *,
    target: Target,
    available: Mapping[str, Sequence[str]] | None = None,
    arms: Sequence[AblationArm] = ARMS,
) -> IncrementalReport:
    """Run EXP-004's five arms and report what each family added."""
    resolved = dict(available) if available is not None else available_from_registry()
    ablation = run_ablation(dataset, target=target, available=resolved, arms=arms)
    return IncrementalReport(ablation=ablation, increments=_increments(ablation, arms, resolved))


def _increments(
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
