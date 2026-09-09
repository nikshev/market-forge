"""EXP-015's strict derivatives/DeFi ablation (REQ-EXP-015)."""

from __future__ import annotations

import pytest

from channelflow.dataset import CertifiedDataset, Label, Row, WalkForwardFolds, certify
from channelflow.research.ablation import AblationArm
from channelflow.research.defi_confluence import (
    ADDS_BOTH_WAYS,
    ADDS_NOTHING,
    CANDIDATE_FAMILIES,
    FAMILIES,
    REDUNDANT,
    UNMEASURED,
    DifferentFolds,
    InstrumentsMissing,
    NotStrict,
    available_from_registry,
    fingerprint,
    require_same_folds,
    run_confluence_ablation,
    strict_arms,
    strictness_violations,
)

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND
INSTRUMENTS = ("BTCUSDT", "ETHUSDT")

#: The features each family owns in these fixtures, supplied explicitly rather
#: than resolved from the registry: none of EXP-015's DEX families has a
#: registered producer yet, and a test that read the registry would be measuring
#: that absence instead of the ablation.
AVAILABLE: dict[str, tuple[str, ...]] = {
    "channel": ("channel_position",),
    "oi_funding_liquidations": ("oi_z",),
    "dex_cex_basis": ("dex_divergence_bps",),
    "dex_depth_asymmetry": ("dex_depth_asymmetry",),
    "swap_imbalance": ("dex_swap_imbalance",),
    "lp_migration": ("dex_lp_migration",),
}
FLOOR = 0.01


def rows(n: int = 60, *, start: int = 0) -> list[Row]:
    """A target `oi_z` decides, with one family that copies it and three that do not.

    `dex_divergence_bps` carries the same information as `oi_z`, which is what
    makes it the fixture's redundant family: added to the baseline alone it
    helps, and added to a set that already contains `oi_z` it adds nothing.
    """
    built = []
    for offset in range(n):
        index = start + offset
        turning = index % 2 == 0
        oi = (1.0 if turning else -1.0) + index * 1e-6
        built.append(
            Row(
                entity=INSTRUMENTS[index % 2],
                as_of_ns=index * SECOND,
                # Every feature carries the same tiny drift, so no two rows
                # share a vector: `require_disjoint` reads a repeated vector as
                # a shared row and refuses a split that is disjoint in time.
                features={
                    "channel_position": float(index % 5) / 5.0 + index * 1e-6,
                    "oi_z": oi,
                    "dex_divergence_bps": oi,
                    "dex_depth_asymmetry": float(index % 3) - 1.0 + index * 1e-6,
                    "dex_swap_imbalance": float(index % 7) / 7.0 + index * 1e-6,
                    "dex_lp_migration": float(index % 11) / 11.0 + index * 1e-6,
                },
                source_max_event_ns=index * SECOND,
                label=Label(
                    label_class="MAX" if turning else "NO_TURN",
                    horizon_end_ns=index * SECOND + HORIZON_NS,
                    available_ns=index * SECOND + HORIZON_NS,
                ),
            )
        )
    return built


def certified(built: list[Row] | None = None, *, folds: int = 3) -> CertifiedDataset:
    built = built if built is not None else rows()
    return certify(built, WalkForwardFolds(horizon_ns=HORIZON_NS, folds=folds).build(built))


def run(dataset: CertifiedDataset | None = None, **kwargs: object):
    return run_confluence_ablation(
        dataset if dataset is not None else certified(),
        target="MAX",
        instruments=INSTRUMENTS,
        improvement_floor=FLOOR,
        available=AVAILABLE,
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.trace("REQ-EXP-015")
def test_the_five_families_the_prd_names_are_ablated() -> None:
    """OI/funding/liquidations; DEX-CEX executable basis; DEX depth asymmetry;
    swap imbalance; LP liquidity migration."""
    assert CANDIDATE_FAMILIES == (
        "oi_funding_liquidations",
        "dex_cex_basis",
        "dex_depth_asymmetry",
        "swap_imbalance",
        "lp_migration",
    )
    assert FAMILIES == ("channel", *CANDIDATE_FAMILIES)

    report = run()

    assert set(report.families) == set(CANDIDATE_FAMILIES)


@pytest.mark.trace("REQ-EXP-015")
def test_every_arm_is_one_family_from_a_reference() -> None:
    """EXP-015's own word: strict.

    An arm two families away from both references still produces a delta, and
    that delta still looks like one family's contribution. It is the sum of two.
    """
    arms = strict_arms()

    assert strictness_violations(arms) == ()
    # The baseline, one arm adding each family, the full set, one arm removing
    # each family.
    assert len(arms) == 2 + 2 * len(CANDIDATE_FAMILIES)


@pytest.mark.trace("REQ-EXP-015")
def test_an_arm_two_families_from_both_references_is_refused() -> None:
    """Rather than scored, because nothing about its number would look wrong."""
    loose = (
        *strict_arms(),
        AblationArm(
            name="plus_two_at_once",
            families=("channel", "swap_imbalance", "lp_migration"),
            taxonomy=FAMILIES,
        ),
    )

    assert strictness_violations(loose) == ("plus_two_at_once",)
    with pytest.raises(NotStrict, match="plus_two_at_once"):
        run(arms=loose)


@pytest.mark.trace("REQ-EXP-015")
def test_every_arm_is_scored_on_one_fold_set() -> None:
    """ "Same walk-forward folds", made into something a reader can check.

    The report carries the fingerprint of the folds it ran on, because "we used
    the same splits" is otherwise a sentence in a method section.
    """
    dataset = certified()

    report = run(dataset)

    assert report.fingerprint == fingerprint(dataset)
    assert report.ablation.folds == len(dataset.folds)


@pytest.mark.trace("REQ-EXP-015")
def test_reports_on_different_folds_cannot_be_compared() -> None:
    """The failure this guards against is a per-family study run separately and
    the numbers put in one table. Nothing about those numbers looks wrong."""
    four = run(certified(folds=4))
    three = run(certified(folds=3))

    require_same_folds([four, four])
    with pytest.raises(DifferentFolds):
        require_same_folds([four, three])


@pytest.mark.trace("REQ-EXP-015")
def test_a_family_is_measured_both_alone_and_in_context() -> None:
    """The two directions answer different questions and here they disagree.

    `dex_divergence_bps` carries the same information as `oi_z`. Added to the
    baseline alone it improves the score; added to a set that already contains
    `oi_z` it adds nothing. A single-direction ablation reports whichever of
    those two facts it happened to measure.
    """
    report = run()

    basis = report.families["dex_cex_basis"]
    assert basis.alone is not None and basis.alone.brier_delta is not None
    assert basis.in_context is not None and basis.in_context.brier_delta is not None
    assert basis.alone.brier_delta <= -FLOOR, "it helps on its own"
    assert basis.in_context.brier_delta > -FLOOR, "and adds nothing to the full set"
    assert basis.reading == REDUNDANT
    assert "dex_cex_basis" in report.redundant


@pytest.mark.trace("REQ-EXP-015")
def test_a_family_that_helps_both_ways_is_named_as_such() -> None:
    """The control, without which `REDUNDANT` everywhere would be consistent
    with an ablation that cannot detect value at all.

    Measured on rows where nothing else carries the target: the fixture's
    duplicate family is dropped, so `oi_z` is the only thing that knows.
    """
    without_the_copy = {**AVAILABLE, "dex_cex_basis": ("dex_depth_asymmetry",)}

    report = run_confluence_ablation(
        certified(),
        target="MAX",
        instruments=INSTRUMENTS,
        improvement_floor=FLOOR,
        available=without_the_copy,
    )

    oi = report.families["oi_funding_liquidations"]
    assert oi.reading == ADDS_BOTH_WAYS


@pytest.mark.trace("REQ-EXP-015")
def test_a_family_that_helps_neither_way_is_named_as_such() -> None:
    """The second control: a feature on a period the label does not follow."""
    report = run()

    assert report.families["lp_migration"].reading == ADDS_NOTHING


@pytest.mark.trace("REQ-EXP-015")
def test_a_family_with_no_features_is_unmeasured_rather_than_worthless() -> None:
    """ "This family added nothing" and "there was nothing to add" are different
    findings, and a zero reports the second as the first."""
    empty = {**AVAILABLE, "swap_imbalance": ()}

    report = run_confluence_ablation(
        certified(),
        target="MAX",
        instruments=INSTRUMENTS,
        improvement_floor=FLOOR,
        available=empty,
    )

    swap = report.families["swap_imbalance"]
    assert swap.reading == UNMEASURED
    assert swap.alone is None or swap.alone.brier_delta is None


@pytest.mark.trace("REQ-EXP-015")
def test_the_instruments_are_required_and_checked_against_the_data() -> None:
    """EXP-015 names BTC and ETH "and other liquid assets".

    A pooled result read as one asset's is a different claim from the one the
    numbers support, and a report naming an asset it never scored is a claim
    about that asset.
    """
    with pytest.raises(InstrumentsMissing):
        run_confluence_ablation(
            certified(),
            target="MAX",
            instruments=(),
            improvement_floor=FLOOR,
            available=AVAILABLE,
        )

    with pytest.raises(InstrumentsMissing, match="SOLUSDT"):
        run_confluence_ablation(
            certified(),
            target="MAX",
            instruments=("BTCUSDT", "SOLUSDT"),
            improvement_floor=FLOOR,
            available=AVAILABLE,
        )

    assert run().instruments == INSTRUMENTS


@pytest.mark.trace("REQ-EXP-015")
def test_the_improvement_floor_is_required_and_positive() -> None:
    """It decides what counts as an improvement, and every reading moves with
    it. PRD section 13A.27's warning applies."""
    with pytest.raises(TypeError):
        run_confluence_ablation(  # type: ignore[call-arg]
            certified(), target="MAX", instruments=INSTRUMENTS, available=AVAILABLE
        )

    with pytest.raises(ValueError, match="improvement_floor"):
        run_confluence_ablation(
            certified(),
            target="MAX",
            instruments=INSTRUMENTS,
            improvement_floor=0.0,
            available=AVAILABLE,
        )


@pytest.mark.trace("REQ-EXP-015")
def test_the_dex_basis_family_does_not_claim_the_cex_perp_basis() -> None:
    """`basis_bps` is PRD section 16's perp-spot basis, a CEX derivatives
    feature. A `basis_` prefix here would put a CEX number in the DEX arm and
    report its contribution as the DEX view's -- the trap EXP-007 walked into."""
    resolved = available_from_registry()

    assert "basis_bps" not in resolved["dex_cex_basis"]
    assert "basis_bps" not in resolved["oi_funding_liquidations"]


@pytest.mark.trace("REQ-EXP-015")
def test_two_runs_produce_equal_reports() -> None:
    dataset = certified()

    first = run(dataset)
    second = run(dataset)

    assert first.families == second.families
    assert first.fingerprint == second.fingerprint


@pytest.mark.trace("REQ-EXP-015")
def test_the_fingerprint_tells_apart_fold_sets_of_the_same_size() -> None:
    """Counting the folds is not identifying them.

    Two studies can both use three folds over different rows, and a fingerprint
    that only carried the count would call those the same splits -- which is the
    exact claim it exists to check.
    """
    here = certified()
    elsewhere = certified(rows(start=10_000))

    assert fingerprint(here).folds == fingerprint(elsewhere).folds
    assert fingerprint(here) != fingerprint(elsewhere)

    with pytest.raises(DifferentFolds):
        require_same_folds([run(here), run(elsewhere)])


@pytest.mark.trace("REQ-EXP-015")
def test_the_improvement_floor_decides_what_counts_as_an_improvement() -> None:
    """Not the sign of the difference.

    Every ablation produces differences; almost all of them are rounding. The
    same family reads as adding value at a floor of a hundredth of a Brier point
    and as adding nothing at a floor no real improvement could clear -- and it
    is the floor doing that, not the data.
    """
    without_the_copy = {**AVAILABLE, "dex_cex_basis": ("dex_depth_asymmetry",)}

    def at(floor: float) -> str:
        report = run_confluence_ablation(
            certified(),
            target="MAX",
            instruments=INSTRUMENTS,
            improvement_floor=floor,
            available=without_the_copy,
        )
        return report.families["oi_funding_liquidations"].reading

    assert at(FLOOR) == ADDS_BOTH_WAYS
    assert at(0.9) == ADDS_NOTHING
