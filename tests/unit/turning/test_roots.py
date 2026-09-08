"""PRD section 13A.12's root filtering, which is Test F (REQ-NRT-F)."""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.turning import (
    PathCoefficients,
    PromotionGate,
    TurnType,
    assess_root_stability,
    derivative_roots,
)

#: A clean peak at h = 3: -(h-3)^2, well inside a horizon of 10.
STABLE = PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=10.0)


@pytest.mark.trace("REQ-NRT-F")
@pytest.mark.trace("REQ-WP-019")
def test_every_assessment_records_the_three_section_13a12_metrics() -> None:
    """SC-006, FR-009.

    Test F's second sentence is an instruction on its own: "Record root
    sensitivity metrics." Not "record them when the root is rejected", and not
    "record them when asked".
    """
    stability = assess_root_stability(STABLE, tolerance=0.05)

    assert stability.presence_rate == pytest.approx(1.0)
    assert stability.horizon_iqr >= 0.0
    assert stability.turn_type_agreement == pytest.approx(1.0)
    assert stability.members > 1
    assert stability.tolerance == pytest.approx(0.05)


@pytest.mark.trace("REQ-NRT-F")
def test_the_same_path_and_tolerance_assess_identically_twice() -> None:
    """SC-006, FR-008, ADR-041.

    Constitution Principle XI. A stability metric that moves between runs
    cannot support the sentence "this root is stable" -- it is the same
    instability one level up.
    """
    first = assess_root_stability(STABLE, tolerance=0.05)
    second = assess_root_stability(STABLE, tolerance=0.05)

    assert first == second


@pytest.mark.trace("REQ-NRT-F")
def test_a_stable_root_survives_the_gate() -> None:
    """FR-010.

    The control for every refusal below: if nothing passed, the refusals would
    prove nothing.
    """
    candidate = derivative_roots(STABLE)[0]
    stability = assess_root_stability(STABLE, tolerance=0.05)

    decision = PromotionGate().assess(candidate, stability)

    assert decision.promoted
    assert decision.failed == ()


@pytest.mark.trace("REQ-NRT-F")
def test_a_root_that_only_some_members_find_is_refused_by_name() -> None:
    """SC-007, FR-009, FR-010.

    PRD section 13A.11: "a root can appear from tiny coefficient changes". This
    path's peak sits at h = 9.9 with a horizon of 10, so a perturbation of a few
    percent pushes it outside -- present for some members and absent for others.
    That is the silent instability Test F is named after.
    """
    # -(h - 9.9)^2, peaking just inside the horizon.
    fragile = PathCoefficients(c0=-98.01, c1=19.8, c2=-1.0, c3=0.0, horizon=10.0)
    candidate = derivative_roots(fragile)[0]
    stability = assess_root_stability(fragile, tolerance=0.10)

    decision = PromotionGate().assess(candidate, stability)

    assert not decision.promoted
    assert "root_presence_rate" in decision.failed
    assert stability.presence_rate < 1.0


@pytest.mark.trace("REQ-NRT-F")
def test_the_metrics_are_recorded_even_when_the_root_is_refused() -> None:
    """FR-009.

    "Record root sensitivity metrics" is unconditional, and the rejected case is
    the one a reader comes back to.
    """
    fragile = PathCoefficients(c0=-98.01, c1=19.8, c2=-1.0, c3=0.0, horizon=10.0)
    candidate = derivative_roots(fragile)[0]
    stability = assess_root_stability(fragile, tolerance=0.10)

    decision = PromotionGate().assess(candidate, stability)

    assert decision.stability is stability
    assert decision.stability.presence_rate is not None


@pytest.mark.trace("REQ-NRT-F")
def test_a_shallow_turn_is_refused_on_curvature() -> None:
    """FR-010.

    Section 13A.12 condition 6: "second derivative magnitude exceeds minimum
    curvature threshold". A turn too gentle to distinguish from a plateau is
    condition 6's whole subject.
    """
    candidate = derivative_roots(STABLE)[0]
    stability = assess_root_stability(STABLE, tolerance=0.05)

    decision = PromotionGate(minimum_curvature=100.0).assess(candidate, stability)

    assert not decision.promoted
    assert "minimum_curvature" in decision.failed


@pytest.mark.trace("REQ-NRT-F")
def test_an_excursion_inside_the_noise_floor_is_refused() -> None:
    """FR-010.

    Section 13A.12 condition 5: the predicted excursion must exceed the fee and
    noise floor. A forecast turn worth less than the cost of trading it is not a
    forecast anyone can act on.
    """
    candidate = derivative_roots(STABLE)[0]
    stability = assess_root_stability(STABLE, tolerance=0.05)

    decision = PromotionGate(noise_floor=1_000.0).assess(candidate, stability)

    assert not decision.promoted
    assert "noise_floor" in decision.failed


@pytest.mark.trace("REQ-NRT-F")
def test_every_failing_condition_is_named_not_just_the_first() -> None:
    """FR-010.

    A gate that stops at the first failure sends the reader back to run it again
    with that one fixed. Section 13A.12 lists eight conditions precisely so a
    rejection can say which held.
    """
    candidate = derivative_roots(STABLE)[0]
    stability = assess_root_stability(STABLE, tolerance=0.05)

    decision = PromotionGate(minimum_curvature=100.0, noise_floor=1_000.0).assess(
        candidate, stability
    )

    assert set(decision.failed) == {"minimum_curvature", "noise_floor"}


@pytest.mark.trace("REQ-NRT-F")
def test_the_thresholds_are_the_prds_research_defaults_and_are_configuration() -> None:
    """FR-011.

    Section 13A.12 gives `root_presence_rate >= 0.70`, `root_horizon_iqr_bars
    <= 3`, `turn_type_agreement >= 0.80`, and then says in its own words that
    these "are research defaults, not assumed production constants". Carrying
    them as defaults on a configuration object is what that sentence asks for;
    hard-coding them into the comparison is what it forbids.
    """
    gate = PromotionGate()

    assert gate.minimum_presence_rate == pytest.approx(0.70)
    assert gate.maximum_horizon_iqr == pytest.approx(3.0)
    assert gate.minimum_turn_type_agreement == pytest.approx(0.80)

    strict = PromotionGate(minimum_presence_rate=0.99)
    assert strict.minimum_presence_rate == pytest.approx(0.99)


@pytest.mark.trace("REQ-NRT-F")
def test_disagreement_about_the_turn_type_is_measured() -> None:
    """FR-009.

    Section 13A.12's `turn_type_agreement`. A root whose members disagree about
    whether it is a top or a bottom is worse than one they cannot find: it has a
    direction, and half of it is wrong.
    """
    stability = assess_root_stability(STABLE, tolerance=0.05)

    assert stability.turn_type_agreement == pytest.approx(1.0)
    assert stability.majority_turn_type is TurnType.MAX


@pytest.mark.trace("REQ-NRT-F")
def test_a_negative_tolerance_is_refused() -> None:
    """FR-008.

    A tolerance of zero perturbs nothing, so every member is the original path
    and the presence rate is 1 by construction -- a stability check that cannot
    fail. Refused rather than allowed to report a reassuring number.
    """
    with pytest.raises(ValueError, match="tolerance"):
        assess_root_stability(STABLE, tolerance=0.0)


@pytest.mark.trace("REQ-NRT-F")
def test_a_path_with_no_root_at_all_reports_zero_presence() -> None:
    """FR-009.

    A straight path. Nothing to promote, and the metrics still exist -- so a
    caller reading `presence_rate == 0` learns why, rather than reading an
    exception and learning that something went wrong.
    """
    straight = PathCoefficients(c0=0.0, c1=2.0, c2=0.0, c3=0.0, horizon=10.0)

    stability = assess_root_stability(straight, tolerance=0.05)

    assert stability.presence_rate == pytest.approx(0.0)
    assert stability.majority_turn_type is None


@pytest.mark.trace("REQ-NRT-F")
@pytest.mark.trace("REQ-WP-019")
def test_the_turning_package_consults_neither_a_clock_nor_a_random_source() -> None:
    """SC-010, FR-015, ADR-041.

    A clock would make a replayed experiment reach a different verdict; a random
    source would make a repeated one reach a different verdict. Test F asks
    whether a root survives perturbation, and neither question can be answered
    by a procedure that does not answer the same way twice.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "turning"
    modules = list(package.glob("*.py"))
    assert modules, "the package moved; this test would otherwise pass by finding nothing"

    for module in modules:
        source = module.read_text()
        for forbidden in (
            "import time",
            "time.time",
            "datetime.now",
            "utcnow",
            "monotonic",
            "import random",
            "np.random",
            "default_rng",
            "RandomState",
        ):
            assert forbidden not in source, f"{module.name} reaches for {forbidden!r}"
