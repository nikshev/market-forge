"""EXP-007: what the DEX view adds over the CEX one, for ETH.

# @trace: REQ-EXP-007

    For ETH: CEX only; CEX + DEX price divergence; + DEX depth asymmetry;
    + swap imbalance; + LP liquidity changes.

The same cumulative shape as EXP-004, over different families, and the same
machinery: each arm contains the previous one and adds exactly one family, so the
difference between neighbours is that family's contribution.

**Every DEX family resolves to nothing today.** [[REQ-WP-015]]'s adapter and
[[REQ-WP-016]]'s cross-venue engine compute divergence, depth asymmetry and swap
imbalance, but none of it is registered as a feature -- so the honest report is
four arms marked not run, with the reason. That is the state of the pipeline, and
saying it is the point: an arm scored on features it does not have reports the
absence of data as the absence of value.

EXP-007 names one instrument, so the report carries it. A DEX result is about a
pool, and the pool is the instrument.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from channelflow.dataset import CertifiedDataset
from channelflow.experiments import Field
from channelflow.research.ablation import AblationArm
from channelflow.research.cumulative import (
    IncrementalReport,
    resolve_membership,
    run_cumulative_ablation,
)
from channelflow.turning.direct import Target

#: EXP-007's families, in its order.
FAMILIES: tuple[str, ...] = (
    "cex",
    "dex_price_divergence",
    "dex_depth_asymmetry",
    "swap_imbalance",
    "lp_liquidity",
)

#: How each family would be found in the registry. The DEX prefixes match
#: nothing today; they are here so that registering those features makes the
#: arms run without anybody editing this file.
_MEMBERSHIP: dict[str, tuple[str, ...]] = {
    "cex": ("channel_", "ofi_", "qi_l1", "depth_imbalance_"),
    # Not `basis_`: the registry's `basis_bps` is PRD section 16's perp-spot
    # basis, a CEX derivatives feature. Matching it here would put a CEX number
    # in the DEX arm and report its contribution as the DEX view's.
    "dex_price_divergence": ("dex_divergence_",),
    "dex_depth_asymmetry": ("dex_depth_asymmetry",),
    "swap_imbalance": ("dex_swap_imbalance",),
    "lp_liquidity": ("dex_lp_",),
}

#: The five arms, cumulative in EXP-007's order.
ARMS: tuple[AblationArm, ...] = tuple(
    AblationArm(name=name, families=FAMILIES[: index + 1], taxonomy=FAMILIES)
    for index, name in enumerate(
        (
            "cex_only",
            "plus_dex_price_divergence",
            "plus_dex_depth_asymmetry",
            "plus_swap_imbalance",
            "plus_lp_liquidity",
        )
    )
)


@dataclass(frozen=True)
class DexIncrementalReport:
    """The cumulative report, and the instrument it is about."""

    instrument: str
    report: IncrementalReport

    @property
    def compared(self) -> Field:
        """The arms of the cumulative ablation underneath."""
        return self.report.compared


EXPERIMENT = "EXP-007"

#: The comparison this module's entry point returns.
COMPARISON = DexIncrementalReport


def available_from_registry() -> dict[str, tuple[str, ...]]:
    """Which registered features belong to each of EXP-007's families.

    Every DEX family comes back empty today. That is not a bug to route around:
    the arms that need them are reported as not run, which is what the pipeline's
    state actually is.
    """
    return resolve_membership(_MEMBERSHIP)


def run_dex_ablation(
    dataset: CertifiedDataset,
    *,
    target: Target,
    instrument: str,
    available: Mapping[str, Sequence[str]] | None = None,
    arms: Sequence[AblationArm] = ARMS,
) -> DexIncrementalReport:
    """Run EXP-007's five arms for one instrument.

    `instrument` has no default. EXP-007 names ETH, and a DEX result is about a
    pool -- a report that did not say which would be a result about nothing in
    particular.
    """
    if not instrument:
        raise ValueError(
            "an instrument is required: EXP-007 names one, and a DEX result is about "
            "a pool rather than about the market in general"
        )
    resolved = dict(available) if available is not None else available_from_registry()
    return DexIncrementalReport(
        instrument=instrument,
        report=run_cumulative_ablation(dataset, target=target, available=resolved, arms=arms),
    )
