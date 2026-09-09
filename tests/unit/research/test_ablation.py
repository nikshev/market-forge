"""An ablation across feature families (REQ-US-006, PRD section 25.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.dataset import Label, Row, WalkForwardFolds
from channelflow.research import (
    ARMS,
    AblationArm,
    ArmEntry,
    UnknownFamily,
    rank_arms,
    run_ablation,
)
from channelflow.turning.direct import DirectBaselineResult

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND


def rows(*, features: dict[str, float] | None = None) -> list[Row]:
    """Rows whose label follows one channel feature, with the rest as noise."""
    built = []
    for index in range(120):
        slope = 1.0 if index % 2 == 0 else -1.0
        values = {
            "channel_slope": slope + index * 1e-6,
            "channel_width_pct": 0.02 + index * 1e-6,
            "ofi_1m": float(index % 5),
            "funding_z": float(index % 7),
        }
        if features is not None:
            values = {**values, **features}
        as_of_ns = index * SECOND
        built.append(
            Row(
                entity="BTCUSDT",
                as_of_ns=as_of_ns,
                features=values,
                source_max_event_ns=as_of_ns,
                label=Label(
                    label_class="MAX" if slope > 0 else "NO_TURN",
                    horizon_end_ns=as_of_ns + HORIZON_NS,
                    available_ns=as_of_ns + HORIZON_NS,
                ),
            )
        )
    return built


#: What the rows above actually carry, by the arm's own family names.
AVAILABLE = {
    "channel": ("channel_slope", "channel_width_pct"),
    "order_flow": ("ofi_1m",),
    "derivatives": ("funding_z",),
    "dex": (),
}


@pytest.fixture
def folds() -> list:
    return WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(rows())


@pytest.mark.trace("REQ-US-006")
def test_all_five_arms_appear_in_the_report(folds: list) -> None:
    """SC-001, FR-002.

    REQ-US-006 names five. An arm silently missing from the report is one the
    reader assumes was compared.
    """
    report = run_ablation(folds, target="MAX", available=AVAILABLE)

    assert {entry.arm for entry in report.entries} == {arm.name for arm in ARMS}
    assert len(ARMS) == 5


@pytest.mark.trace("REQ-US-006")
def test_every_scored_arm_ran_on_the_same_folds(folds: list) -> None:
    """SC-002, FR-003.

    EXP-015 says it in the PRD's own words: "use strict ablation and same
    walk-forward folds". Arms scored on different splits differ by the split.
    """
    report = run_ablation(folds, target="MAX", available=AVAILABLE)

    assert report.folds == len(folds)
    scored = [e for e in report.entries if e.result is not None]
    assert scored
    assert len({e.result.rows_scored for e in scored if e.result is not None}) == 1


@pytest.mark.trace("REQ-US-006")
def test_an_arm_with_no_features_for_its_families_is_not_run(folds: list) -> None:
    """SC-003, FR-004.

    The registry carries no DEX features today. Reported as a result, "channel +
    DEX" would score exactly what "channel only" scored, and a reader would take
    that as evidence the DEX family adds nothing -- a finding about the data
    pipeline presented as a finding about the market.
    """
    report = run_ablation(folds, target="MAX", available=AVAILABLE)

    dex = next(e for e in report.entries if e.arm == "channel_dex")
    assert dex.result is None
    assert "dex" in dex.reason


@pytest.mark.trace("REQ-US-006")
def test_an_arm_identical_to_an_earlier_one_names_it(folds: list) -> None:
    """SC-004, FR-005.

    Two arms resolving to one feature set are one measurement reported twice.
    Said plainly, the reader knows why the numbers match.
    """
    # A taxonomy overlap: both families resolve to the same feature. Distinct
    # names, one measurement -- which is different from a family with no data,
    # and has to read differently.
    available = {**AVAILABLE, "derivatives": ("ofi_1m",)}

    report = run_ablation(folds, target="MAX", available=available)

    derivatives = next(e for e in report.entries if e.arm == "channel_derivatives")
    assert derivatives.result is None
    assert "channel_order_flow" in derivatives.reason


@pytest.mark.trace("REQ-US-006")
def test_an_unrun_arm_is_not_ranked(folds: list) -> None:
    """SC-005, FR-006.

    A ranking is an ordering of things that were measured.
    """
    report = run_ablation(folds, target="MAX", available=AVAILABLE)

    assert "channel_dex" not in report.ranking
    assert set(report.ranking) <= {e.arm for e in report.entries if e.result is not None}


@pytest.mark.trace("REQ-US-006")
def test_the_ranking_breaks_ties_by_name(folds: list) -> None:
    """FR-007, SC-007.

    Two arms that score identically must order the same way twice, or the
    report's conclusion changes between runs over one input.
    """
    first = run_ablation(folds, target="MAX", available=AVAILABLE)
    second = run_ablation(folds, target="MAX", available=AVAILABLE)

    assert first.ranking == second.ranking
    assert first == second


@pytest.mark.trace("REQ-US-006")
def test_a_report_with_nothing_runnable_says_so(folds: list) -> None:
    """SC-006, FR-008.

    An empty ranking reads like a completed comparison in which nothing won.
    """
    report = run_ablation(
        folds,
        target="MAX",
        available={"channel": (), "order_flow": (), "derivatives": (), "dex": ()},
    )

    assert report.ranking == ()
    assert not report.runnable
    assert "no arm" in report.summary


@pytest.mark.trace("REQ-US-006")
def test_an_unknown_family_is_refused() -> None:
    """SC-008, FR-001.

    A family the taxonomy does not know resolves to no features, which is
    indistinguishable from a family whose data is missing -- and one of those is
    a typo.
    """
    with pytest.raises(UnknownFamily, match="sentiment"):
        AblationArm(name="channel_sentiment", families=("channel", "sentiment"))


@pytest.mark.trace("REQ-US-006")
def test_adding_a_family_can_only_add_features(folds: list) -> None:
    """SC-002, FR-009.

    "All combined" contains every other arm's features. If it did not, the
    comparison would not be an ablation -- the arms would differ in more than
    the family under test.
    """
    combined = next(arm for arm in ARMS if arm.name == "all_combined")
    channel_only = next(arm for arm in ARMS if arm.name == "channel_only")

    assert set(channel_only.families) <= set(combined.families)
    assert set(combined.resolve(AVAILABLE)) >= set(channel_only.resolve(AVAILABLE))


@pytest.mark.trace("REQ-US-006")
def test_all_combined_contains_every_other_arms_families() -> None:
    """SC-002, FR-002.

    "All combined" is the arm every other one is measured against. Missing a
    family, it is another partial arm under a name that claims otherwise, and
    the ablation's headline comparison silently changes meaning.
    """
    combined = next(arm for arm in ARMS if arm.name == "all_combined")

    for arm in ARMS:
        assert set(arm.families) <= set(combined.families), arm.name


@pytest.mark.trace("REQ-US-006")
def test_a_feature_in_two_families_is_counted_once() -> None:
    """FR-001, FR-009.

    A taxonomy where one feature belongs to two families is ordinary -- funding
    is derivatives context and order flow both. Listed twice, the design matrix
    carries a duplicated column, which is a different model from the one the arm
    names, and the arm's ordering would depend on which family came first.
    """
    arm = AblationArm(name="both", families=("order_flow", "derivatives"))
    overlapping = {"order_flow": ("ofi_1m", "funding_z"), "derivatives": ("funding_z",)}

    assert arm.resolve(overlapping) == ("funding_z", "ofi_1m")

    reversed_arm = AblationArm(name="both", families=("derivatives", "order_flow"))
    assert reversed_arm.resolve(overlapping) == arm.resolve(overlapping)


@pytest.mark.trace("REQ-US-006")
def test_the_research_package_consults_no_clock_or_random_source() -> None:
    """SC-009, FR-011."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "research"
    modules = list(package.glob("*.py"))
    assert modules, "the package moved; this test would otherwise pass by finding nothing"

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "import random", "np.random"):
            assert forbidden not in source, f"{module.name} reaches for {forbidden!r}"


@pytest.mark.trace("REQ-US-006")
def test_two_arms_that_score_identically_rank_by_name() -> None:
    """FR-007, SC-007.

    Two arms over different features almost never score identically, so a
    ranking that depended on entry order would agree with itself on every
    realistic input and disagree on the one that matters. Built by hand, in
    reverse, so only the tie-break can produce the answer.
    """
    tied = [
        ArmEntry(arm="zebra", features=("a",), result=_result(0.25)),
        ArmEntry(arm="alpha", features=("b",), result=_result(0.25)),
    ]

    assert rank_arms(tied) == ("alpha", "zebra")
    assert rank_arms(list(reversed(tied))) == ("alpha", "zebra")


def _result(brier: float) -> DirectBaselineResult:
    return DirectBaselineResult(folds=(), rows_scored=10, model_brier=brier, base_rate_brier=0.5)
