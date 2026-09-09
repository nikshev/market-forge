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

from channelflow.dataset import CertifiedDataset
from channelflow.research.ablation import AblationArm
from channelflow.research.cumulative import (
    IncrementalReport,
    resolve_membership,
    run_cumulative_ablation,
)
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


def available_from_registry() -> dict[str, tuple[str, ...]]:
    """Which registered features belong to each of EXP-004's families."""
    return resolve_membership(_MEMBERSHIP)


def run_ofi_ablation(
    dataset: CertifiedDataset,
    *,
    target: Target,
    available: Mapping[str, Sequence[str]] | None = None,
    arms: Sequence[AblationArm] = ARMS,
) -> IncrementalReport:
    """Run EXP-004's five arms and report what each family added."""
    resolved = dict(available) if available is not None else available_from_registry()
    return run_cumulative_ablation(dataset, target=target, available=resolved, arms=arms)
