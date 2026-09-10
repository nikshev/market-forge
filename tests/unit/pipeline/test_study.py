"""One research run, end to end (REQ-WP-024)."""

from __future__ import annotations

import pytest

from channelflow.dataset import CertifiedDataset
from channelflow.experiments import (
    CodeVersion,
    ModelAbsence,
    NotReproducible,
    Registry,
    dataset_reference,
)
from channelflow.lakehouse import InMemoryObjectStore
from channelflow.models import ModelRegistry, combined_artifact
from channelflow.pipeline import NothingScorable, StudyResult, run_study
from tests.unit.conftest import HORIZON_NS

COMMIT = "a" * 40
DATASET = dataset_reference({"feature_snapshots": (1, "c" * 64)})
FEATURES = ("slope", "curvature")


def study(
    dataset: CertifiedDataset,
    *,
    store: InMemoryObjectStore,
    dirty: bool = False,
    minimum_observations: int = 10,
) -> StudyResult:
    return run_study(
        dataset,
        store=store,
        code=CodeVersion(commit=COMMIT, dirty=dirty),
        experiment="EXP-008",
        target="MAX",
        feature_names=FEATURES,
        dataset_ref=DATASET,
        as_of_ns=1_000,
        minimum_observations=minimum_observations,
    )


@pytest.fixture
def store() -> InMemoryObjectStore:
    return InMemoryObjectStore()


@pytest.mark.trace("REQ-WP-024")
def test_every_variant_is_registered_and_on_record(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """The whole point: five mechanisms that had no caller, called."""
    result = study(certified(signal_rows), store=store)

    models = ModelRegistry(store=store)
    runs = Registry(store=store)

    assert result.registrations
    assert len(models.entries()) == len(result.registrations)
    assert {run.variant for run in runs.runs()} == set(result.identities)
    assert all(entry.artifact_hash for entry in models.entries())


@pytest.mark.trace("REQ-WP-024")
def test_the_fourth_hash_resolves_instead_of_reading_unrecorded(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """Before this, every run that fitted a model recorded `UNRECORDED`."""
    result = study(certified(signal_rows), store=store)

    models = ModelRegistry(store=store)
    for identity in result.identities.values():
        assert identity.model_artifact is not ModelAbsence.UNRECORDED
        assert isinstance(identity.model_artifact, str)
        assert models.holds(identity.model_artifact)


@pytest.mark.trace("REQ-WP-024")
def test_a_variant_that_lost_is_on_record_too(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """PRD section 41 rule 11 is about the ones that did not survive."""
    result = study(certified(signal_rows), store=store)

    runs = Registry(store=store)
    outcomes = {run.variant: run.outcome for run in runs.runs()}

    assert set(outcomes) == set(result.identities)
    assert len(outcomes) > 1
    assert len([o for o in outcomes.values() if str(o) == "kept"]) <= 1


@pytest.mark.trace("REQ-WP-024")
def test_a_variant_s_artifact_covers_its_folds_rather_than_one_of_them(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """The run cites the variant *as run*, once per fold.

    Taking one fold's artifact would still register, still resolve, and still
    give two identical runs the same hash -- and would name a model fitted on a
    quarter of the data as the thing the result came from.
    """
    result = study(certified(signal_rows), store=store)

    assert result.scored_folds > 1
    for registration in result.registrations:
        folds = [
            next(
                score.artifact
                for score in (report.model, *report.baselines)
                if score.name == registration.model_type and score.artifact is not None
            )
            for report in result.comparison.folds
        ]
        assert len(folds) == result.scored_folds
        assert registration.artifact_hash == combined_artifact(folds)
        assert registration.artifact_hash not in folds


@pytest.mark.trace("REQ-WP-024")
def test_a_dirty_tree_stops_the_report_and_says_so(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """The refusal is the acceptance. A run wired so the four hashes are
    assembled and never refused would satisfy a careless reading of this
    requirement while leaving every refusal as theoretical as before."""
    with pytest.raises(NotReproducible, match="commit"):
        study(certified(signal_rows), store=store, dirty=True)


@pytest.mark.trace("REQ-WP-024")
def test_a_dirty_run_is_still_recorded_before_it_is_refused(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """ADR-054: recording is unconditional. Refusing to record would leave no
    trace of the run at all, which is the outcome rule 11 is against."""
    with pytest.raises(NotReproducible):
        study(certified(signal_rows), store=store, dirty=True)

    runs = Registry(store=store)
    assert runs.runs()
    assert all(not run.reproducible for run in runs.runs())


@pytest.mark.trace("REQ-WP-024")
def test_two_runs_over_one_dataset_produce_equal_identities(certified, signal_rows) -> None:
    """Principle XI at the end of the research path. Same dataset, same code,
    same variants -- so the same run hashes, which is what makes a result
    citable at all."""
    dataset = certified(signal_rows)

    first = study(dataset, store=InMemoryObjectStore())
    second = study(dataset, store=InMemoryObjectStore())

    assert {name: i.run_hash for name, i in first.identities.items()} == {
        name: i.run_hash for name, i in second.identities.items()
    }


@pytest.mark.trace("REQ-WP-024")
def test_reliability_is_reported_at_each_horizon(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    result = study(certified(signal_rows), store=store)

    assert set(result.reliability.slices) == {HORIZON_NS}
    assert result.reliability.slices[HORIZON_NS].observations > 0


@pytest.mark.trace("REQ-WP-024")
def test_a_thin_horizon_says_so_rather_than_showing_a_curve(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    result = study(certified(signal_rows), store=store, minimum_observations=10**6)

    assert result.reliability.slices[HORIZON_NS].curve is None


@pytest.mark.trace("REQ-WP-024")
def test_a_dataset_with_nothing_scorable_is_refused(certified, store) -> None:
    """Rather than reported as a run with an empty field, which would put a
    result on record that measured nothing."""
    from tests.unit.conftest import _row

    flat = [
        _row(
            index,
            features={"slope": float(index) * 1e-6, "curvature": float(index) * 1e-6},
            label_class="NO_TURN",
        )
        for index in range(120)
    ]

    with pytest.raises(NothingScorable):
        study(certified(flat), store=store)


@pytest.mark.trace("REQ-WP-024")
def test_a_winner_is_published_only_when_something_beat_the_base_rate(
    certified, signal_rows, signal_free_rows, store: InMemoryObjectStore
) -> None:
    """A model that cannot beat a base rate is not a model, so nothing is
    promoted -- and the field is still on record."""
    learnable = study(certified(signal_rows), store=store)
    assert learnable.report is not None

    noise = study(certified(signal_free_rows), store=InMemoryObjectStore())
    assert noise.report is None
    assert noise.identities


@pytest.mark.trace("REQ-WP-024")
def test_an_artifact_only_resolves_against_the_registry_that_holds_it(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """The registration has to happen before the citation.

    The identities a run produced are checked against an empty registry here:
    every one is refused, naming its artifact. That is what the run's own check
    would report if the order were ever swapped, and it is why the check is not
    decoration.
    """
    from channelflow.models import require_registered

    result = study(certified(signal_rows), store=store)
    elsewhere = ModelRegistry(store=InMemoryObjectStore())

    for identity in result.identities.values():
        with pytest.raises(NotReproducible, match="registration"):
            require_registered(identity, models=elsewhere)


@pytest.mark.trace("REQ-WP-024")
def test_the_registration_carries_the_run_s_real_spans(
    certified, signal_rows, store: InMemoryObjectStore
) -> None:
    """They held 1/2/2/3 until [[ADR-058]].

    A registry whose whole job is to describe an artifact truthfully carried
    four invented numbers, because the rule it was written against refused any
    overlap and a walk-forward run cannot satisfy that. The spans are now the
    folds' own, and they overlap -- correctly.
    """
    dataset = certified(signal_rows)

    result = study(dataset, store=store)

    train = [row.as_of_ns for fold in dataset.folds for row in fold.train]
    validate = [row.as_of_ns for fold in dataset.folds for row in fold.validate]
    for registration in result.registrations:
        assert registration.validation_regime == "walk_forward"
        assert registration.train_start_ns == min(train)
        assert registration.train_end_ns == max(train)
        assert registration.validation_start_ns == min(validate)
        assert registration.validation_end_ns == max(validate)
    # The overlap that the first version of the rule refused.
    assert min(validate) < max(train)
