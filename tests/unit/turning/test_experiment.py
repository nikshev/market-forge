"""The GMDH forward-path derivative experiment (REQ-WP-019 criterion 5)."""

from __future__ import annotations

import pytest

from channelflow.dataset import Row, certify
from channelflow.turning import (
    PathCoefficients,
    PromotionGate,
    Verdict,
    run_derivative_experiment,
)
from channelflow.turning.direct import FeatureMissing

from .conftest import Certify

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND
FEATURES = ("slope", "curvature")


def _paths(rows: list[Row]) -> dict[int, PathCoefficients]:
    """A forward path per row, determined by its own features.

    Label-side by PRD section 24.2's permission: this is what the path turned
    out to be, which a target may know and a feature may not. Rows whose slope
    is positive peak at h = 3; the rest run straight.
    """
    built = {}
    for row in rows:
        if row.features["slope"] > 0.5:
            # -(h - 3)^2, a clean peak inside the horizon.
            built[row.as_of_ns] = PathCoefficients(c0=-9.0, c1=6.0, c2=-1.0, c3=0.0, horizon=10.0)
        else:
            built[row.as_of_ns] = PathCoefficients(c0=0.0, c1=-2.0, c2=0.0, c3=0.0, horizon=10.0)
    return built


@pytest.mark.trace("REQ-WP-019")
def test_a_signal_free_experiment_returns_no_edge_and_raises_nothing(
    signal_free_rows: list[Row], certified: Certify
) -> None:
    """SC-008, FR-012, FR-013, ADR-042.

    REQ-WP-019's fifth acceptance criterion in its own words: the experiment
    "can return `NO_EDGE` without blocking product completion". An exception is
    precisely a research result that blocks.
    """
    dataset = certified(signal_free_rows)

    outcome = run_derivative_experiment(
        dataset,
        feature_names=FEATURES,
        path_targets=_paths(signal_free_rows),
        target="MAX",
    )

    assert outcome.verdict is Verdict.NO_EDGE
    assert outcome.reason


@pytest.mark.trace("REQ-WP-019")
def test_an_experiment_with_an_edge_says_so(signal_rows: list[Row], certified: Certify) -> None:
    """SC-008.

    The control. Without a case that reaches `EDGE`, `NO_EDGE` everywhere would
    be consistent with an experiment that cannot conclude anything at all.
    """
    dataset = certified(signal_rows)

    outcome = run_derivative_experiment(
        dataset,
        feature_names=FEATURES,
        path_targets=_paths(signal_rows),
        target="MAX",
    )

    assert outcome.verdict is Verdict.EDGE
    assert outcome.promoted


@pytest.mark.trace("REQ-WP-019")
def test_every_outcome_carries_its_report_and_its_stability_metrics(
    signal_rows: list[Row], certified: Certify
) -> None:
    """FR-013.

    A verdict without them is a conclusion the reader has to trust. With them it
    is one they can check -- and Test F's "record root sensitivity metrics"
    applies to the experiment's output as much as to the gate's.
    """
    dataset = certified(signal_rows)

    outcome = run_derivative_experiment(
        dataset,
        feature_names=FEATURES,
        path_targets=_paths(signal_rows),
        target="MAX",
    )

    assert outcome.report is not None
    assert outcome.stability is not None
    assert outcome.stability.members > 1


@pytest.mark.trace("REQ-WP-019")
def test_roots_that_no_gate_would_promote_are_reported_with_their_reasons(
    signal_rows: list[Row], certified: Certify
) -> None:
    """SC-008, FR-013.

    A gate nothing can pass. The verdict is `NO_EDGE`, and every rejection names
    the conditions that failed -- otherwise the reader reruns the experiment to
    learn what the gate already knew.
    """
    dataset = certified(signal_rows)

    outcome = run_derivative_experiment(
        dataset,
        feature_names=FEATURES,
        path_targets=_paths(signal_rows),
        target="MAX",
        gate=PromotionGate(noise_floor=1_000_000.0),
    )

    assert outcome.verdict is Verdict.NO_EDGE
    assert outcome.promoted == ()
    assert outcome.rejected
    assert all("noise_floor" in decision.failed for decision in outcome.rejected)


@pytest.mark.trace("REQ-WP-019")
def test_too_little_data_is_a_verdict_not_a_crash(
    signal_rows: list[Row], certified: Certify
) -> None:
    """SC-008, FR-012.

    "Not enough data" is a finding about the experiment, and a finding belongs
    in the outcome. Raising it would stop the product for a research result --
    the exact coupling [[ADR-023]] recorded and this criterion removes.
    """
    dataset = certified(signal_rows)
    starved = [fold for fold in dataset.folds if len(fold.train) < 4] or [dataset.folds[0]]
    trimmed = [
        type(fold)(
            index=fold.index,
            train=fold.train[:1],
            validate=fold.validate,
            purged=fold.purged,
            embargoed=fold.embargoed,
        )
        for fold in starved
    ]

    outcome = run_derivative_experiment(
        certify(signal_rows, trimmed),
        feature_names=FEATURES,
        path_targets=_paths(signal_rows),
        target="MAX",
    )

    assert outcome.verdict is Verdict.NO_EDGE
    assert "fold" in outcome.reason


@pytest.mark.trace("REQ-WP-019")
def test_a_caller_error_still_raises(signal_rows: list[Row], certified: Certify) -> None:
    """FR-012.

    `NO_EDGE` is a research conclusion, not a catch-all. A feature the rows do
    not carry is a mistake in the call, and returning "no edge" for it would
    report a finding about the market that is really a finding about the code.
    """
    dataset = certified(signal_rows)

    with pytest.raises(FeatureMissing):
        run_derivative_experiment(
            dataset,
            feature_names=("slope", "depth"),
            path_targets=_paths(signal_rows),
            target="MAX",
        )


@pytest.mark.trace("REQ-WP-019")
def test_a_row_without_a_forward_path_is_refused(
    signal_rows: list[Row], certified: Certify
) -> None:
    """FR-012.

    Silently skipping unlabelled rows would shrink the experiment's evidence
    without saying so, and a smaller sample is how a weak result becomes a
    strong-looking one.
    """
    dataset = certified(signal_rows)
    paths = _paths(signal_rows)
    paths.pop(next(iter(paths)))

    with pytest.raises(KeyError, match="forward path"):
        run_derivative_experiment(dataset, feature_names=FEATURES, path_targets=paths, target="MAX")
