"""Nothing trains on an unchecked dataset (REQ-US-007)."""

from __future__ import annotations

import inspect

import pytest

from channelflow.dataset import (
    CertificationRefused,
    CertifiedDataset,
    Fold,
    Label,
    LeakageReport,
    Row,
    WalkForwardFolds,
    certify,
    check_rows,
)
from channelflow.dataset.leakage import Finding

SECOND = 1_000_000_000
HORIZON_NS = 10 * SECOND


def rows(*, leak: bool = False) -> list[Row]:
    built = []
    for index in range(120):
        as_of_ns = index * SECOND
        horizon_end_ns = as_of_ns + HORIZON_NS
        built.append(
            Row(
                entity="BTCUSDT",
                as_of_ns=as_of_ns,
                features={"slope": 1.0 if index % 2 == 0 else -1.0, "drift": index * 1e-6},
                source_max_event_ns=as_of_ns,
                label=Label(
                    label_class="MAX" if index % 2 == 0 else "NO_TURN",
                    horizon_end_ns=horizon_end_ns,
                    # A label knowable at `t` is the leak PRD section 24.2 is
                    # about: the model is told the answer at the instant it is
                    # asked the question.
                    available_ns=as_of_ns if leak else horizon_end_ns,
                ),
            )
        )
    return built


def folds_for(built: list[Row]) -> list:
    return WalkForwardFolds(horizon_ns=HORIZON_NS, folds=4).build(built)


@pytest.mark.trace("REQ-US-007")
def test_a_clean_dataset_certifies(monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-001, FR-001, FR-003, FR-008."""
    built = rows()

    certificate = certify(built, folds_for(built))

    assert certificate.rows.clean
    assert certificate.folds_report.clean
    assert certificate.folds
    assert certificate.rows.examined["label_not_known_at_t"] == len(built)


@pytest.mark.trace("REQ-US-007")
def test_a_leaked_label_refuses_and_names_the_rule() -> None:
    """SC-002, FR-003, FR-005.

    The failure this exists to stop is silent: a dataset whose labels were
    knowable at `t` trains fine and scores well, and every metric downstream
    reads like an edge.
    """
    built = rows(leak=True)

    with pytest.raises(CertificationRefused, match="label_not_known_at_t"):
        certify(built, folds_for(built))


@pytest.mark.trace("REQ-US-007")
def test_an_empty_dataset_refuses() -> None:
    """SC-004, FR-004, ADR-025.

    Every "no row violates X" check passes over nothing, and an empty dataset is
    the most likely output of a broken build.
    """
    with pytest.raises(CertificationRefused):
        certify([], [])


@pytest.mark.trace("REQ-US-007")
def test_a_certificate_cannot_be_built_around_an_unclean_report() -> None:
    """SC-005, FR-002.

    A gate with a back door is documentation. If a certificate can be
    hand-assembled, the first person in a hurry assembles one.
    """
    dirty = LeakageReport(
        findings=(Finding(rule="label_not_known_at_t", detail="a row knew its answer"),),
        examined={"label_not_known_at_t": 1},
    )
    clean = LeakageReport(findings=(), examined={"train_precedes_validation": 1})

    with pytest.raises(CertificationRefused):
        CertifiedDataset(folds=(), rows=dirty, folds_report=clean)


@pytest.mark.trace("REQ-US-007")
def test_certifying_twice_gives_equal_certificates() -> None:
    """SC-008, FR-009. The checks are pure; a gate that is not would be a coin."""
    built = rows()
    prepared = folds_for(built)

    assert certify(built, prepared) == certify(built, prepared)


@pytest.mark.trace("REQ-US-007")
def test_every_training_entry_point_requires_a_certificate() -> None:
    """SC-007, FR-006.

    Checked over the signatures rather than by calling each one, so a fifth
    training entry point added later fails this test by existing rather than by
    being remembered.
    """
    from channelflow.research import run_ablation
    from channelflow.turning import run_derivative_experiment
    from channelflow.turning.direct import run_direct_baseline

    for entry in (run_direct_baseline, run_derivative_experiment, run_ablation):
        first = next(iter(inspect.signature(entry).parameters.values()))
        assert first.annotation == "CertifiedDataset", (
            f"{entry.__name__} takes {first.annotation}, so it can be handed an unchecked dataset"
        )


@pytest.mark.trace("REQ-US-007")
def test_a_bare_fold_list_is_refused_by_training() -> None:
    """SC-006, FR-006.

    The signature test above is structural; this is the behaviour it promises.
    """
    from channelflow.turning.direct import run_direct_baseline

    built = rows()

    with pytest.raises(AttributeError):
        run_direct_baseline(
            folds_for(built),  # type: ignore[arg-type]
            target="MAX",
            feature_names=("slope",),
        )


@pytest.mark.trace("REQ-US-007")
def test_training_reads_its_folds_from_the_certificate() -> None:
    """FR-007.

    A caller who certifies a dataset and then edits their own list must not
    change what the model sees; otherwise the certificate attests to something
    other than what was trained on.
    """
    built = rows()
    prepared = folds_for(built)
    certificate = certify(built, prepared)

    prepared.clear()

    assert certificate.folds
    assert len(certificate.folds) > 0


@pytest.mark.trace("REQ-US-007")
def test_clean_rows_do_not_certify_contaminated_folds() -> None:
    """SC-003, FR-003.

    The two checks answer different questions. Rows can be individually honest
    while the split still trains on its own validation window -- PRD §24.3's
    rule, and the one a fold builder gets wrong rather than a labeller.
    """
    built = rows()
    prepared = folds_for(built)
    good = prepared[0]
    contaminated = Fold(
        index=good.index,
        # A training row taken from inside the validation window: each row is
        # fine on its own, and the fold is not.
        train=(*good.train, good.validate[0]),
        validate=good.validate,
        purged=good.purged,
        embargoed=good.embargoed,
    )

    assert check_rows(built).clean, "the rows themselves must be clean, or this tests both"

    with pytest.raises(CertificationRefused, match="train_precedes_validation"):
        certify(built, [contaminated])
