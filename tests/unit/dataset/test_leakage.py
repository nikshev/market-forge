"""The checks that say whether a dataset is honest (REQ-WP-017).

Every check here gets a test that constructs the violation. A check nobody has
seen fail is a check nobody knows works -- and these are the checks a model's
honesty will rest on, so "probably fine" is not a standard they can be held to.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from channelflow.dataset import (
    Fold,
    Row,
    WalkForwardFolds,
    check_folds,
    check_rows,
)

from .conftest import BASE_NS, ENTITY, MINUTE_NS, row


@dataclass
class StubLabel:
    label_class: str
    horizon_end_ns: int
    available_ns: int
    extremum_time_ns: int | None = None


@dataclass
class StubRow:
    """A row that did not come through `Row`.

    `Row` refuses every violation below at construction -- `model_construct`
    included, since pydantic still runs `model_post_init`. A checker that could
    only be handed a `Row` could therefore never see a violation, and would be
    untestable in the way that looks like it works.

    That is not a workaround: it is what the checker is for. Rows will arrive
    from Parquet, from a database, from a later implementation of this module,
    and none of those routes runs the constructor.
    """

    entity: str
    as_of_ns: int
    features: dict[str, float]
    source_max_event_ns: int
    label: StubLabel


def leaking_row(*, at: int, source_at: int) -> StubRow:
    """Features that saw past their own as-of time."""
    return StubRow(
        entity=ENTITY,
        as_of_ns=BASE_NS + at * MINUTE_NS,
        features={"qi_l1": 0.5},
        source_max_event_ns=BASE_NS + source_at * MINUTE_NS,
        label=StubLabel(
            label_class="NO_TURN",
            horizon_end_ns=BASE_NS + (at + 10) * MINUTE_NS,
            available_ns=BASE_NS + (at + 10) * MINUTE_NS,
        ),
    )


@pytest.mark.trace("REQ-WP-017")
def test_a_clean_dataset_passes_and_says_what_it_examined(
    clean_rows: list[Row],
) -> None:
    """SC-009. ADR-025: "clean" means something was checked."""
    report = check_rows(clean_rows)

    assert report.clean
    assert report.examined["feature_not_after_t"] == len(clean_rows)
    assert all(count > 0 for count in report.examined.values() if count is not None)


@pytest.mark.trace("REQ-WP-017")
def test_an_empty_dataset_fails_rather_than_passing_clean() -> None:
    """SC-010, FR-016, ADR-025.

    Every other check here is "no row violates X", which passes trivially over
    nothing. A build that silently produced nothing, followed by a report
    saying everything is clean, reads exactly like success.
    """
    report = check_rows([])

    assert not report.clean
    assert report.findings[0].rule == "non_empty"
    assert "clean" in report.findings[0].detail


@pytest.mark.trace("REQ-WP-017")
def test_a_feature_from_after_t_is_caught_and_named() -> None:
    """SC-009, FR-017. PRD section 24.2's rule, over a built dataset."""
    report = check_rows([row(at=1), leaking_row(at=5, source_at=9)])

    assert not report.clean
    leak = next(f for f in report.findings if f.rule == "feature_not_after_t")
    assert leak.row_index == 1
    assert leak.field == "source_max_event_ns"


@pytest.mark.trace("REQ-WP-017")
@pytest.mark.trace("REQ-BIAS-003")
def test_a_label_available_before_its_extremum_is_caught() -> None:
    """SC-009, PRD section 41 rule 3. The defect the whole labeller exists to
    avoid, checked again from the outside."""
    bad = StubRow(
        entity=ENTITY,
        as_of_ns=BASE_NS + 10 * MINUTE_NS,
        features={"qi_l1": 0.5},
        source_max_event_ns=BASE_NS + 10 * MINUTE_NS,
        label=StubLabel(
            label_class="MAX",
            horizon_end_ns=BASE_NS + 40 * MINUTE_NS,
            available_ns=BASE_NS + 15 * MINUTE_NS,
            extremum_time_ns=BASE_NS + 20 * MINUTE_NS,
        ),
    )

    report = check_rows([bad])

    assert any(f.rule == "label_available_at_confirmation" for f in report.findings)


@pytest.mark.trace("REQ-WP-017")
def test_a_label_already_knowable_at_t_is_caught() -> None:
    """A label available at or before its own row's time is a feature, not a
    target -- and it would be the single most effective way to make a model
    look prescient."""
    report = check_rows([row(at=10, horizon=10, available=5)])

    assert any(f.rule == "label_not_known_at_t" for f in report.findings)


@pytest.mark.trace("REQ-WP-017")
def test_clean_folds_pass(clean_rows: list[Row]) -> None:
    """SC-009."""
    folds = WalkForwardFolds(horizon_ns=10 * MINUTE_NS, folds=4).build(clean_rows)

    report = check_folds(folds)

    assert report.clean
    assert report.examined["horizon_purged"] > 0


@pytest.mark.trace("REQ-WP-017")
def test_an_unpurged_horizon_is_caught(clean_rows: list[Row]) -> None:
    """SC-009, PRD section 24.3.

    A fold assembled without the purge: the training rows' horizons reach into
    the validation window, so the model was trained on the answer.
    """
    unpurged = Fold(
        index=0,
        train=tuple(clean_rows[:20]),
        validate=tuple(clean_rows[15:25]),
        purged=0,
        embargoed=0,
    )

    report = check_folds([unpurged])

    assert not report.clean
    assert any(f.rule == "horizon_purged" for f in report.findings)
    assert any(f.rule == "train_precedes_validation" for f in report.findings)


@pytest.mark.trace("REQ-WP-017")
def test_no_folds_fails_rather_than_passing_clean() -> None:
    """SC-010, ADR-025, on the other checker too."""
    report = check_folds([])

    assert not report.clean
    assert report.findings[0].rule == "non_empty"
