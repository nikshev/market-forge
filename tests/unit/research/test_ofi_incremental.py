"""EXP-004's cumulative order-flow ablation (REQ-EXP-004)."""

from __future__ import annotations

import pytest

from channelflow.dataset import CertifiedDataset, Label, Row, WalkForwardFolds, certify
from channelflow.research.ablation import UnknownFamily
from channelflow.research.ofi_incremental import (
    ARMS,
    FAMILIES,
    AblationArm,
    available_from_registry,
    run_ofi_ablation,
)

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND

#: What the rows below carry, by EXP-004's own family names.
AVAILABLE = {
    "channel": ("channel_slope_normalized", "channel_width_pct"),
    "l1_imbalance": ("qi_l1",),
    "multi_level_imbalance": ("depth_imbalance_5",),
    "ofi": ("ofi_1m",),
    "persistence_cancellation": ("wall_persistence_ns",),
}


def dataset() -> CertifiedDataset:
    rows = []
    for index in range(120):
        slope = 1.0 if index % 2 == 0 else -1.0
        as_of_ns = index * SECOND
        rows.append(
            Row(
                entity="BTCUSDT",
                as_of_ns=as_of_ns,
                features={
                    "channel_slope_normalized": slope + index * 1e-6,
                    "channel_width_pct": 0.5 + index * 1e-6,
                    "qi_l1": float(index % 3),
                    "depth_imbalance_5": float(index % 4),
                    "ofi_1m": slope * 2.0,
                    "wall_persistence_ns": float(index % 5),
                },
                source_max_event_ns=as_of_ns,
                label=Label(
                    label_class="MAX" if slope > 0 else "NO_TURN",
                    horizon_end_ns=as_of_ns + HORIZON_NS,
                    available_ns=as_of_ns + HORIZON_NS,
                ),
            )
        )
    return certify(rows, WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(rows))


@pytest.mark.trace("REQ-EXP-004")
def test_the_five_arms_are_the_prds_and_are_cumulative() -> None:
    """The first derived criterion, and what makes the differences readable.

    Arms that differed in more than the family under test would report the sum
    of every difference between them.
    """
    assert [arm.name for arm in ARMS] == [
        "channel_only",
        "plus_l1_imbalance",
        "plus_multi_level_imbalance",
        "plus_ofi",
        "plus_persistence_cancellation",
    ]
    for previous, arm in zip(ARMS, ARMS[1:], strict=False):
        assert set(previous.families) < set(arm.families)
        assert len(arm.families) == len(previous.families) + 1


@pytest.mark.trace("REQ-EXP-004")
def test_every_arm_appears_in_the_report() -> None:
    """A variant silently missing is one the conclusion never considered."""
    report = run_ofi_ablation(dataset(), target="MAX", available=AVAILABLE)

    assert {entry.arm for entry in report.ablation.entries} == {arm.name for arm in ARMS}


@pytest.mark.trace("REQ-EXP-004")
def test_each_increment_names_what_it_added() -> None:
    """ "Incremental value" is a difference, and a difference needs both sides
    named. The absolute scores are in the ablation; these are the deltas."""
    report = run_ofi_ablation(dataset(), target="MAX", available=AVAILABLE)

    assert [i.arm for i in report.increments] == [arm.name for arm in ARMS[1:]]
    by_arm = {i.arm: i for i in report.increments}
    assert by_arm["plus_ofi"].over == "plus_multi_level_imbalance"
    assert by_arm["plus_ofi"].added_features == ("ofi_1m",)


@pytest.mark.trace("REQ-EXP-004")
def test_an_increment_over_an_unscored_arm_is_absent_not_zero() -> None:
    """ "This family added nothing" and "there was nothing to add it to" are
    different findings, and a zero says the first."""
    without_l1 = {**AVAILABLE, "l1_imbalance": ()}

    report = run_ofi_ablation(dataset(), target="MAX", available=without_l1)

    by_arm = {i.arm: i for i in report.increments}
    assert by_arm["plus_l1_imbalance"].brier_delta is None
    assert "not scored" in by_arm["plus_l1_imbalance"].note


@pytest.mark.trace("REQ-EXP-004")
def test_a_family_with_no_features_is_reported_as_not_run() -> None:
    """The second criterion every comparison-shaped experiment shares."""
    without_walls = {**AVAILABLE, "persistence_cancellation": ()}

    report = run_ofi_ablation(dataset(), target="MAX", available=without_walls)

    entry = next(e for e in report.ablation.entries if e.arm == "plus_persistence_cancellation")
    assert entry.result is None
    assert "persistence_cancellation" in entry.reason


@pytest.mark.trace("REQ-EXP-004")
def test_every_arm_is_scored_on_the_same_folds() -> None:
    """EXP-015's instruction, which governs every ablation here."""
    prepared = dataset()

    report = run_ofi_ablation(prepared, target="MAX", available=AVAILABLE)

    assert report.ablation.folds == len(prepared.folds)
    scored = [e for e in report.ablation.entries if e.result is not None]
    assert len({e.result.rows_scored for e in scored if e.result}) == 1


@pytest.mark.trace("REQ-EXP-004")
def test_the_families_are_resolved_from_the_registry() -> None:
    """An arm cannot claim a feature that does not exist, and cannot miss one
    that does: the membership is prefixes over `REGISTRY`, so a feature added to
    the book module joins its arm without anyone remembering to list it."""
    found = available_from_registry()

    assert set(found) == set(FAMILIES)
    assert "qi_l1" in found["l1_imbalance"]
    # Non-empty first: `all()` over an empty tuple is true, so a membership rule
    # that matched nothing would satisfy the shape assertions below while
    # emptying the arm it defines.
    assert found["ofi"], "the OFI arm resolved to nothing"
    assert found["multi_level_imbalance"], "the multi-level arm resolved to nothing"
    assert found["channel"], "the channel arm needs registered features to be a baseline"
    assert all(name.startswith("ofi_") for name in found["ofi"])
    assert all(name.startswith("depth_imbalance_") for name in found["multi_level_imbalance"])


@pytest.mark.trace("REQ-EXP-004")
def test_an_arm_naming_a_family_outside_this_taxonomy_is_refused() -> None:
    """EXP-004 slices the registry more finely than REQ-US-006 does, and its arms
    are checked against its own vocabulary rather than against nothing."""
    with pytest.raises(UnknownFamily, match="sentiment"):
        AblationArm(name="bad", families=("channel", "sentiment"), taxonomy=FAMILIES)


@pytest.mark.trace("REQ-EXP-004")
def test_the_us_006_taxonomy_still_refuses_this_ones_families() -> None:
    """The two vocabularies are separate on purpose. If EXP-004's families were
    silently accepted by the default taxonomy, an arm could name a group that
    experiment does not measure."""
    with pytest.raises(UnknownFamily):
        AblationArm(name="bad", families=("l1_imbalance",))


@pytest.mark.trace("REQ-EXP-004")
def test_two_runs_produce_equal_reports() -> None:
    prepared = dataset()

    first = run_ofi_ablation(prepared, target="MAX", available=AVAILABLE)
    second = run_ofi_ablation(prepared, target="MAX", available=AVAILABLE)

    assert first == second


@pytest.mark.trace("REQ-EXP-004")
def test_a_family_that_helps_moves_the_increment_the_right_way() -> None:
    """The sign is the finding.

    Here the channel features are noise and OFI carries the label, so adding OFI
    must improve the score. Lower Brier is better, so the delta is negative --
    and a sign taken the other way round would report the one family that
    worked as the one that hurt.
    """
    rows = []
    for index in range(120):
        signal = 1.0 if index % 2 == 0 else -1.0
        as_of_ns = index * SECOND
        rows.append(
            Row(
                entity="BTCUSDT",
                as_of_ns=as_of_ns,
                features={
                    "channel_slope_normalized": float(index % 5) + index * 1e-6,
                    "channel_width_pct": float(index % 7),
                    "qi_l1": float(index % 3),
                    "depth_imbalance_5": float(index % 4),
                    "ofi_1m": signal * 3.0,
                    "wall_persistence_ns": float(index % 5),
                },
                source_max_event_ns=as_of_ns,
                label=Label(
                    label_class="MAX" if signal > 0 else "NO_TURN",
                    horizon_end_ns=as_of_ns + HORIZON_NS,
                    available_ns=as_of_ns + HORIZON_NS,
                ),
            )
        )
    prepared = certify(rows, WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(rows))

    report = run_ofi_ablation(prepared, target="MAX", available=AVAILABLE)

    by_arm = {i.arm: i for i in report.increments}
    assert by_arm["plus_ofi"].brier_delta is not None
    assert by_arm["plus_ofi"].brier_delta < 0.0


@pytest.mark.trace("REQ-EXP-004")
def test_the_families_resolve_in_a_process_that_imported_nothing_else() -> None:
    """The registry fills as its producing modules are imported.

    Read cold, it holds only whatever happened to be loaded already -- which
    made every order-flow arm look empty the first time this ran. Inside the
    test suite the modules are imported by other files, so the bug is invisible;
    a fresh process is the only place it shows.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from channelflow.research.ofi_incremental import available_from_registry as a;"
            "print(sum(len(v) for v in a().values()))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert int(result.stdout.strip()) > 10
