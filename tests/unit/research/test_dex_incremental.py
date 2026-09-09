"""EXP-007's cumulative DEX ablation, for ETH (REQ-EXP-007)."""

from __future__ import annotations

import pytest

from channelflow.dataset import CertifiedDataset, Label, Row, WalkForwardFolds, certify
from channelflow.research.ablation import UnknownFamily
from channelflow.research.dex_incremental import (
    ARMS,
    FAMILIES,
    AblationArm,
    available_from_registry,
    run_dex_ablation,
)

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND

#: A caller who has DEX features, which the registry does not yet.
SUPPLIED = {
    "cex": ("channel_slope_normalized", "ofi_1m"),
    "dex_price_divergence": ("dex_divergence_bps",),
    "dex_depth_asymmetry": ("dex_depth_asymmetry",),
    "swap_imbalance": ("dex_swap_imbalance",),
    "lp_liquidity": ("dex_lp_change",),
}


def dataset() -> CertifiedDataset:
    rows = []
    for index in range(120):
        signal = 1.0 if index % 2 == 0 else -1.0
        as_of_ns = index * SECOND
        rows.append(
            Row(
                entity="ETHUSDT",
                as_of_ns=as_of_ns,
                features={
                    "channel_slope_normalized": float(index % 5) + index * 1e-6,
                    "ofi_1m": float(index % 3),
                    "dex_divergence_bps": signal * 4.0,
                    "dex_depth_asymmetry": float(index % 4),
                    "dex_swap_imbalance": float(index % 7),
                    "dex_lp_change": float(index % 6),
                },
                source_max_event_ns=as_of_ns,
                label=Label(
                    label_class="MAX" if signal > 0 else "NO_TURN",
                    horizon_end_ns=as_of_ns + HORIZON_NS,
                    available_ns=as_of_ns + HORIZON_NS,
                ),
            )
        )
    return certify(rows, WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(rows))


@pytest.mark.trace("REQ-EXP-007")
def test_the_five_arms_are_the_prds_and_are_cumulative() -> None:
    """CEX only, then divergence, depth asymmetry, swap imbalance, LP changes."""
    assert [arm.name for arm in ARMS] == [
        "cex_only",
        "plus_dex_price_divergence",
        "plus_dex_depth_asymmetry",
        "plus_swap_imbalance",
        "plus_lp_liquidity",
    ]
    for previous, arm in zip(ARMS, ARMS[1:], strict=False):
        assert set(previous.families) < set(arm.families)
        assert len(arm.families) == len(previous.families) + 1


@pytest.mark.trace("REQ-EXP-007")
def test_the_report_names_the_instrument() -> None:
    """EXP-007 names ETH. A DEX result is about a pool, and a report that did not
    say which would be a result about nothing in particular."""
    report = run_dex_ablation(
        dataset(), target="MAX", instrument="ETH/USDC 0.05%", available=SUPPLIED
    )

    assert report.instrument == "ETH/USDC 0.05%"


@pytest.mark.trace("REQ-EXP-007")
def test_the_instrument_is_required() -> None:
    """No default, for the same reason it is reported at all."""
    with pytest.raises(ValueError, match="instrument is required"):
        run_dex_ablation(dataset(), target="MAX", instrument="", available=SUPPLIED)


@pytest.mark.trace("REQ-EXP-007")
def test_every_dex_family_is_empty_in_the_registry_today() -> None:
    """The honest state of the pipeline, asserted rather than assumed.

    REQ-WP-015's adapter and REQ-WP-016's engine compute divergence, depth
    asymmetry and swap imbalance; none of it is registered as a feature. When
    that changes this test fails, which is the right way to find out -- the arms
    start running and the report stops saying "not run".
    """
    found = available_from_registry()

    assert found["cex"], "the CEX arm must have features, or the baseline is empty too"
    for family in ("dex_price_divergence", "dex_depth_asymmetry", "swap_imbalance", "lp_liquidity"):
        assert found[family] == (), f"{family} now resolves; update EXP-007's expectations"


@pytest.mark.trace("REQ-EXP-007")
def test_with_the_registry_as_it_is_every_dex_arm_reports_not_run() -> None:
    """The report a caller gets today. An arm scored on features it does not
    have reports the absence of data as the absence of value."""
    # The DEX families come from the registry, where they are empty; the CEX
    # family is narrowed to what these rows carry, because an arm demanding a
    # feature a row does not have is refused -- a different failure from the one
    # under test.
    from_registry = available_from_registry()
    report = run_dex_ablation(
        dataset(),
        target="MAX",
        instrument="ETH",
        available={**from_registry, "cex": ("channel_slope_normalized", "ofi_1m")},
    )

    entries = {e.arm: e for e in report.report.ablation.entries}
    assert entries["cex_only"].result is not None
    for name in (
        "plus_dex_price_divergence",
        "plus_dex_depth_asymmetry",
        "plus_swap_imbalance",
        "plus_lp_liquidity",
    ):
        assert entries[name].result is None
        assert entries[name].reason


@pytest.mark.trace("REQ-EXP-007")
def test_supplied_features_make_the_arms_run() -> None:
    """The same experiment, given the features it needs.

    Without this the module would only ever be observed in its not-run state,
    and the scoring path would be untested.
    """
    report = run_dex_ablation(dataset(), target="MAX", instrument="ETH", available=SUPPLIED)

    scored = [e for e in report.report.ablation.entries if e.result is not None]
    assert len(scored) == len(ARMS)


@pytest.mark.trace("REQ-EXP-007")
def test_the_divergence_family_shows_its_increment() -> None:
    """Divergence carries the label in this fixture, so adding it must improve
    the score. Lower Brier is better, so the increment is negative."""
    report = run_dex_ablation(dataset(), target="MAX", instrument="ETH", available=SUPPLIED)

    by_arm = {i.arm: i for i in report.report.increments}
    assert by_arm["plus_dex_price_divergence"].added_features == ("dex_divergence_bps",)
    assert by_arm["plus_dex_price_divergence"].brier_delta is not None
    assert by_arm["plus_dex_price_divergence"].brier_delta < 0.0


@pytest.mark.trace("REQ-EXP-007")
def test_an_arm_naming_a_family_outside_this_taxonomy_is_refused() -> None:
    """EXP-007's vocabulary is its own, like EXP-004's."""
    with pytest.raises(UnknownFamily, match="l1_imbalance"):
        AblationArm(name="bad", families=("cex", "l1_imbalance"), taxonomy=FAMILIES)


@pytest.mark.trace("REQ-EXP-007")
def test_two_runs_produce_equal_reports() -> None:
    prepared = dataset()

    first = run_dex_ablation(prepared, target="MAX", instrument="ETH", available=SUPPLIED)
    second = run_dex_ablation(prepared, target="MAX", instrument="ETH", available=SUPPLIED)

    assert first == second
