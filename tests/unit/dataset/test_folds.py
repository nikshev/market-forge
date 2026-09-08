"""PRD section 24.3's chronological folds (REQ-WP-017, REQ-BIAS-001, REQ-BIAS-010).

- prefer chronological walk-forward splits;
- apply purge/embargo where overlapping horizon would contaminate
  validation;
- never random-shuffle train/test for primary evaluation.
"""

from __future__ import annotations

import pytest

from channelflow.dataset import (
    FoldConfigurationImpossible,
    LockedTestSplit,
    Row,
    ShufflingRefused,
    WalkForwardFolds,
)

from .conftest import MINUTE_NS, row

HORIZON_NS = 10 * MINUTE_NS


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-001")
def test_folds_are_chronological(clean_rows: list[Row]) -> None:
    """SC-005, FR-010. Every training row precedes every validation row."""
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(clean_rows)

    assert folds
    for fold in folds:
        assert max(r.as_of_ns for r in fold.train) < min(r.as_of_ns for r in fold.validate)


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-001")
def test_shuffling_is_refused(clean_rows: list[Row]) -> None:
    """SC-006, FR-010, PRD section 41 rule 1.

    Labels here overlap in time, so a shuffled split validates on rows whose
    horizons the training set already saw -- and the score is a memory.
    """
    with pytest.raises(ShufflingRefused, match="rule 1"):
        WalkForwardFolds(horizon_ns=HORIZON_NS).build(clean_rows, shuffle=True)


@pytest.mark.trace("REQ-WP-017")
def test_training_rows_whose_horizon_reaches_validation_are_purged(
    clean_rows: list[Row],
) -> None:
    """SC-005, FR-011. The part that is easy to leave out and impossible to
    notice missing.

    A label at `t` describes what happened until `t + H`. If `t` is in training
    and `t + H` is inside the validation window, the model was trained on the
    answer.
    """
    folds = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(clean_rows)

    for fold in folds:
        window_start = fold.validate[0].as_of_ns
        for training_row in fold.train:
            assert training_row.label.horizon_end_ns < window_start

    assert any(fold.purged > 0 for fold in folds), (
        "the purge must actually remove something, or this test proves nothing"
    )


@pytest.mark.trace("REQ-WP-017")
def test_the_embargo_is_reported(clean_rows: list[Row]) -> None:
    """FR-012. Rows just after a validation window share its market state."""
    without = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(clean_rows)
    with_embargo = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4, embargo_ns=5 * MINUTE_NS).build(
        clean_rows
    )

    assert sum(f.embargoed for f in with_embargo) > sum(f.embargoed for f in without)


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-010")
def test_the_test_split_is_locked_until_explicitly_unlocked(
    clean_rows: list[Row],
) -> None:
    """SC-007, FR-013, PRD section 41 rule 10.

    A method that raises, not a flag someone reads and ignores: asking for the
    test split during tuning is an error carrying the rule in its message.
    """
    builder = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4)
    builder.build(clean_rows)

    with pytest.raises(LockedTestSplit, match="rule 10"):
        builder.test_split()

    builder.unlock()
    assert builder.test_split(), "unlocking must actually give the split"


@pytest.mark.trace("REQ-WP-017")
def test_too_few_rows_for_the_configured_folds_is_refused() -> None:
    """The spec's fourth edge case: silently producing fewer folds would hide
    that the configuration cannot work."""
    with pytest.raises(FoldConfigurationImpossible, match="cannot make"):
        WalkForwardFolds(horizon_ns=HORIZON_NS, folds=10).build([row(at=i) for i in range(4)])


@pytest.mark.trace("REQ-WP-017")
def test_a_horizon_that_purges_everything_is_refused() -> None:
    """The spec's third edge case. A fold trained on nothing is not a fold, and
    returning it empty would produce a validation score from an untrained
    model."""
    rows = [row(at=i, horizon=500) for i in range(60)]

    with pytest.raises(FoldConfigurationImpossible, match="purge"):
        WalkForwardFolds(horizon_ns=500 * MINUTE_NS, folds=4).build(rows)


@pytest.mark.trace("REQ-WP-017")
def test_building_is_deterministic(clean_rows: list[Row]) -> None:
    """Principle XI. Two builds of one configuration give one dataset."""
    first = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(clean_rows)
    second = WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(clean_rows)

    assert [(f.index, len(f.train), len(f.validate)) for f in first] == [
        (f.index, len(f.train), len(f.validate)) for f in second
    ]
