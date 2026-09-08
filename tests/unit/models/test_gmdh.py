"""The GMDH search (REQ-WP-018, PRD section 23)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from channelflow.models import (
    GMDHNetwork,
    NotEnoughData,
    SplitOverlap,
    StopReason,
)


@pytest.mark.trace("REQ-WP-018")
def test_selection_uses_data_the_node_was_not_fitted_on(
    structured: tuple[np.ndarray, ...],
) -> None:
    """SC-001, FR-001, ADR-030.

    A node fitting its own rows perfectly and generalizing badly must be
    pruned. Here the scoring split is a *different* relationship from the
    fitting split, so any node that scored on its training rows would look
    excellent and this assertion would fail.
    """
    x_fit, y_fit, x_score, _ = structured
    # The scoring target is inverted: nothing fitted on `y_fit` can score well
    # on it, and a search selecting on training error would not notice.
    y_wrong = 1.0 - (x_score[:, 0] * x_score[:, 1] > 0.0).astype(np.float64)

    network = GMDHNetwork(max_layers=3)
    result = network.fit_with_selection(x_fit, y_fit, x_score, y_wrong)

    assert result.best_score > 0.2, (
        "a node scored against a contradictory target cannot look good; if it "
        "does, selection is reading the fitting split"
    )


@pytest.mark.trace("REQ-WP-018")
def test_overlapping_splits_are_refused(structured: tuple[np.ndarray, ...]) -> None:
    """SC-002, FR-002, ADR-030.

    Comparing the two row sets costs nothing. A search that quietly selected on
    its own training data would produce a plausible model and a good-looking
    report, and nothing downstream would contradict it.
    """
    x_fit, y_fit, _, _ = structured

    with pytest.raises(SplitOverlap, match="memoriser"):
        GMDHNetwork().fit_with_selection(x_fit, y_fit, x_fit, y_fit)


@pytest.mark.trace("REQ-WP-018")
def test_the_layer_budget_is_respected(structured: tuple[np.ndarray, ...]) -> None:
    """SC-003, FR-003."""
    x_fit, y_fit, x_score, y_score = structured

    result = GMDHNetwork(max_layers=2).fit_with_selection(x_fit, y_fit, x_score, y_score)

    assert result.depth <= 2


@pytest.mark.trace("REQ-WP-018")
def test_the_width_budget_is_respected(structured: tuple[np.ndarray, ...]) -> None:
    """SC-003, FR-003."""
    x_fit, y_fit, x_score, y_score = structured

    result = GMDHNetwork(survivors_per_layer=2).fit_with_selection(x_fit, y_fit, x_score, y_score)

    assert all(len(layer) <= 2 for layer in result.layers)


@pytest.mark.trace("REQ-WP-018")
def test_a_search_names_why_it_stopped(structured: tuple[np.ndarray, ...]) -> None:
    """SC-004, FR-005. A search that just ends leaves a reader guessing whether
    it found everything or gave up."""
    x_fit, y_fit, x_score, y_score = structured

    result = GMDHNetwork(max_layers=8).fit_with_selection(x_fit, y_fit, x_score, y_score)

    assert result.stop_reason in set(StopReason)
    assert isinstance(result.stop_reason.value, str)


@pytest.mark.trace("REQ-WP-018")
def test_the_search_stops_when_a_layer_stops_improving(
    unstructured: tuple[np.ndarray, ...],
) -> None:
    """SC-004, FR-004.

    On pure noise there is no structure to find, so the second layer cannot
    improve on the first and the search must stop rather than growing to its
    budget. A search that grew anyway would be memorising -- and the criterion
    is computed on held-out data precisely so it cannot.
    """
    x_fit, y_fit, x_score, y_score = unstructured

    result = GMDHNetwork(max_layers=6).fit_with_selection(x_fit, y_fit, x_score, y_score)

    assert result.stop_reason is StopReason.NO_IMPROVEMENT
    assert result.depth < 6


@pytest.mark.trace("REQ-WP-018")
def test_too_few_inputs_is_refused() -> None:
    """FR-006. One column cannot be paired."""
    x = np.array([[1.0], [2.0], [3.0]])
    y = np.array([0.0, 1.0, 0.0])

    with pytest.raises(NotEnoughData, match="two inputs"):
        GMDHNetwork().fit_with_selection(x, y, x + 100, y)


@pytest.mark.trace("REQ-WP-018")
def test_a_single_row_scoring_split_is_refused(
    structured: tuple[np.ndarray, ...],
) -> None:
    """FR-006, the spec's fourth edge case: a criterion computed on one row
    selects noise."""
    x_fit, y_fit, x_score, y_score = structured

    with pytest.raises(NotEnoughData, match="one row"):
        GMDHNetwork().fit_with_selection(x_fit, y_fit, x_score[:1], y_score[:1])


@pytest.mark.trace("REQ-WP-018")
def test_a_constant_target_is_refused(structured: tuple[np.ndarray, ...]) -> None:
    """FR-006, the spec's fifth edge case: every model predicts it perfectly,
    so the comparison would be meaningless."""
    x_fit, _, x_score, y_score = structured

    with pytest.raises(NotEnoughData, match="constant"):
        GMDHNetwork().fit_with_selection(x_fit, np.zeros(len(x_fit)), x_score, y_score)


@pytest.mark.trace("REQ-WP-018")
def test_the_protocol_fit_refuses_rather_than_inventing_a_split(
    structured: tuple[np.ndarray, ...],
) -> None:
    """ADR-030. Splitting here would choose a rule -- random, chronological --
    that PRD section 41 rules 1 and 10 are specifically about."""
    x_fit, y_fit, _, _ = structured

    with pytest.raises(NotEnoughData, match="fit_with_selection"):
        GMDHNetwork().fit(x_fit, y_fit)


@pytest.mark.trace("REQ-WP-018")
def test_interactions_resolve_to_original_input_names(
    structured: tuple[np.ndarray, ...],
) -> None:
    """SC-005, FR-008, PRD section 23.1's first named role.

    Node indices would be meaningless to a reader: the second layer's input 0
    is the first layer's best node, not a feature.
    """
    x_fit, y_fit, x_score, y_score = structured
    names = ("channel_position", "ofi_30s", "funding_z", "oi_change")

    network = GMDHNetwork(max_layers=3)
    network.fit_with_selection(x_fit, y_fit, x_score, y_score, input_names=names)
    interactions = network.interactions()

    assert interactions
    first_layer = [i for i in interactions if i[2] == 0]
    assert all(left in names and right in names for left, right, _ in first_layer)


@pytest.mark.trace("REQ-WP-018")
def test_training_is_deterministic(structured: tuple[np.ndarray, ...]) -> None:
    """SC-008, FR-012, Principle XI."""
    x_fit, y_fit, x_score, y_score = structured

    first = GMDHNetwork().fit_with_selection(x_fit, y_fit, x_score, y_score)
    second = GMDHNetwork().fit_with_selection(x_fit, y_fit, x_score, y_score)

    assert first.best_score == second.best_score
    assert first.stop_reason == second.stop_reason
    assert [[(n.left, n.right) for n in layer] for layer in first.layers] == [
        [(n.left, n.right) for n in layer] for layer in second.layers
    ]


@pytest.mark.trace("REQ-WP-018")
def test_the_models_package_cannot_consult_a_clock() -> None:
    """SC-009, FR-013."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "models"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
