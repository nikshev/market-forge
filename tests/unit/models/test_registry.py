"""A fitted model is registered, hashed and citable (REQ-WP-022)."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from channelflow.experiments import (
    CodeVersion,
    ModelAbsence,
    NotReproducible,
    RunIdentity,
    config_hash,
    dataset_reference,
)
from channelflow.lakehouse import Catalog
from channelflow.models import (
    ElasticNetLogistic,
    GradientBoostedTrees,
    LogisticRegression,
    ModelNotFitted,
    ModelRegistry,
    Registration,
    artifact_hash,
    combined_artifact,
    require_registered,
)


def data(seed: int = 0, rows: int = 80) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(rows, 3))
    y = (x[:, 0] + 0.5 * x[:, 1] > 0).astype(np.float64)
    return x, y


def fitted(model: object = None, *, seed: int = 0) -> LogisticRegression:
    del model
    trained = LogisticRegression()
    x, y = data(seed)
    trained.fit(x, y)
    return trained


# --- the hash ---------------------------------------------------------------


@pytest.mark.trace("REQ-WP-022")
def test_two_identical_fits_hash_alike() -> None:
    """What makes an artifact citable: a result naming this hash can be checked
    against a model refitted from the same data."""
    assert artifact_hash(fitted()) == artifact_hash(fitted())


@pytest.mark.trace("REQ-WP-022")
def test_a_model_fitted_on_other_data_hashes_differently() -> None:
    assert artifact_hash(fitted(seed=0)) != artifact_hash(fitted(seed=1))


@pytest.mark.trace("REQ-WP-022")
def test_two_models_with_one_hyperparameter_apart_hash_differently() -> None:
    """A model is what it learned *and* how it was told to learn.

    Two that landed on identical weights from different penalties are not one
    artifact: one of them behaves differently on the next dataset, and a hash
    merging them would certify a reproduction that is not one.
    """
    x, y = data()
    lenient = ElasticNetLogistic(penalty=0.0, l1_ratio=0.5)
    strict = ElasticNetLogistic(penalty=0.9, l1_ratio=0.5)
    lenient.fit(x, y)
    strict.fit(x, y)

    assert artifact_hash(lenient) != artifact_hash(strict)


@pytest.mark.trace("REQ-WP-022")
def test_an_unfitted_model_is_refused_rather_than_hashed() -> None:
    """A hash of an unfitted model would be a stable, meaningless string that
    every unfitted model of that type shares -- and it would certify runs that
    never happened."""
    with pytest.raises(ModelNotFitted, match="logistic_regression"):
        artifact_hash(LogisticRegression())


@pytest.mark.trace("REQ-WP-022")
def test_every_model_type_can_say_whether_it_is_fitted() -> None:
    """Only the model knows: one holds `None` weights, another empty trees, a
    third an absent search result. There is no test from outside that covers
    all three, which is why the protocol asks."""
    x, y = data()
    for model in (
        LogisticRegression(),
        ElasticNetLogistic(penalty=0.1, l1_ratio=0.5),
        GradientBoostedTrees(),
    ):
        assert not model.fitted
        model.fit(x, y)
        assert model.fitted
        assert artifact_hash(model)


@pytest.mark.trace("REQ-WP-022")
def test_a_hyperparameter_alone_changes_the_hash() -> None:
    """Isolated, because the obvious test is not.

    Two `ElasticNetLogistic`s with different penalties also fit to different
    weights, so a hash covering only the fitted state passes that test. Here the
    fitted state is copied unchanged and one hyperparameter moves, which is the
    only thing left to tell them apart.
    """
    trained = fitted()
    same_weights_other_rate = dataclasses.replace(trained, learning_rate=0.2)

    assert same_weights_other_rate._weights is trained._weights
    assert artifact_hash(same_weights_other_rate) != artifact_hash(trained)


@pytest.mark.trace("REQ-WP-022")
def test_a_difference_below_printing_precision_changes_the_hash() -> None:
    """Exact bytes, not a rounded repr.

    Two fits differing in the last bit produce different probabilities, so they
    are different models. A hash that rounded them together would lie about the
    one thing it exists to certify -- and both of these print identically.
    """
    trained = fitted()
    nudged = dataclasses.replace(trained, _bias=trained._bias + 1e-16)

    assert repr(nudged._bias) != "" and nudged._bias != trained._bias
    assert artifact_hash(nudged) != artifact_hash(trained)


@pytest.mark.trace("REQ-WP-022")
def test_an_array_reshaped_without_changing_a_byte_changes_the_hash() -> None:
    """The same buffer under a different shape is a different model: it predicts
    differently, or not at all. Hashing only `tobytes()` would call them one."""
    trained = fitted()
    assert trained._weights is not None
    reshaped = dataclasses.replace(trained, _weights=trained._weights.reshape(-1, 1))

    assert reshaped._weights.tobytes() == trained._weights.tobytes()
    assert artifact_hash(reshaped) != artifact_hash(trained)


@pytest.mark.trace("REQ-WP-022")
def test_two_states_that_concatenate_alike_do_not_hash_alike() -> None:
    """Every part is preceded by its length, so no field can borrow a character
    from the next.

    The pair below is a real collision, not an illustrative one: without the
    lengths these two produce identical bytes, because the tag byte that starts
    the value is indistinguishable from the last character of the key. Found by
    searching for one -- the first shape tried, two plain string fields, cannot
    collide at all, because the field names between them anchor every position.
    A mapping has no such anchors, and a model holding per-feature scaler
    parameters keyed by feature name is exactly that shape.
    """

    @dataclasses.dataclass
    class WithScalers:
        scalers: dict[str, str]
        fitted: bool = True

    assert artifact_hash(WithScalers({"a": "sb"})) != artifact_hash(WithScalers({"as": "b"}))


@pytest.mark.trace("REQ-WP-022")
def test_the_hash_is_framed_so_fields_cannot_borrow_from_each_other() -> None:
    """The same reasoning REQ-REPRO-001's run hash was built on: two different
    models whose fields concatenate to one string must not share a hash."""
    first = GradientBoostedTrees(trees=2, max_depth=11)
    second = GradientBoostedTrees(trees=21, max_depth=1)
    x, y = data()
    first.fit(x, y)
    second.fit(x, y)

    assert artifact_hash(first) != artifact_hash(second)


@pytest.mark.trace("REQ-WP-024")
def test_a_variant_s_artifact_covers_every_fold_and_their_order() -> None:
    """SC-002's "and not otherwise", which is the half a looser reading drops.

    A combined hash that took only the first fold, or that sorted the folds,
    would pass every test that merely checks two identical runs agree -- and
    would call two different walk-forward orders the same run.
    """
    folds = ("a" * 64, "b" * 64, "c" * 64)

    assert combined_artifact(folds) != combined_artifact(folds[:1])
    assert combined_artifact(folds) != combined_artifact(tuple(reversed(folds)))
    assert combined_artifact(folds) != combined_artifact((folds[0], folds[1], "d" * 64))
    assert combined_artifact(folds) == combined_artifact(folds)


@pytest.mark.trace("REQ-WP-024")
def test_a_variant_with_no_scored_fold_has_no_artifact() -> None:
    """Combining nothing would produce a stable hash every empty variant
    shares, and a run could then cite it."""
    with pytest.raises(ModelNotFitted, match="no scored fold"):
        combined_artifact([])


# --- the registration -------------------------------------------------------


def registration(**overrides: object) -> Registration:
    fields: dict[str, object] = {
        "model_type": "logistic_regression",
        "feature_set_versions": {"order_flow": 3},
        "train_start_ns": 1_000,
        "train_end_ns": 2_000,
        "validation_start_ns": 2_000,
        "validation_end_ns": 3_000,
        "code_commit": "a" * 40,
        "hyperparameters": {"iterations": 400},
        "scaler_parameters": {"mean": 0.0},
        "calibration_model": "isotonic",
        "validation_regime": "single_split",
        "metrics": {"brier": 0.19},
        "artifact_hash": "b" * 64,
        "deployment_status": "shadow",
    }
    fields.update(overrides)
    return Registration(**fields)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-022")
def test_a_registration_carries_every_field_section_23_9_names() -> None:
    entry = registration()

    assert entry.model_type
    assert entry.feature_set_versions
    assert entry.code_commit
    assert entry.hyperparameters
    assert entry.metrics
    assert entry.artifact_hash
    assert entry.deployment_status


@pytest.mark.trace("REQ-WP-022")
@pytest.mark.parametrize(
    "field", ["model_type", "code_commit", "calibration_model", "deployment_status"]
)
def test_an_empty_named_field_is_refused(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        registration(**{field: ""})


@pytest.mark.trace("REQ-WP-022")
def test_a_registration_with_no_metrics_is_refused() -> None:
    """A model registered with no measurement was not evaluated, and PRD section
    45's Phase 7 acceptance turns on measurements."""
    with pytest.raises(ValueError, match="metrics"):
        registration(metrics={})


@pytest.mark.trace("REQ-WP-022")
def test_a_single_split_whose_validation_overlaps_its_training_is_refused() -> None:
    """A model validated on rows it was trained on is not validated, and the
    number it reports is the one PRD section 41 rule 10 exists to stop.

    For a single split, and only for one: the spans are the whole of what
    happened, so an overlap between them is the leak itself.
    """
    with pytest.raises(ValueError, match="overlap"):
        registration(validation_start_ns=1_500)


@pytest.mark.trace("REQ-WP-022")
def test_a_walk_forward_run_may_report_overlapping_spans() -> None:
    """The correction.

    Walk-forward folds interleave by construction: fold 1 trains on data later
    than fold 0 validated on. Within a fold the two never touch -- which is the
    property that matters and the one the fold builder and the leakage
    certificate actually enforce. A run-level span pair for such a run overlaps
    and is not a leak, and the earlier rule refused it, which is why
    `run_study` was left writing placeholder spans instead of true ones.
    """
    entry = registration(
        validation_regime="walk_forward",
        train_start_ns=0,
        train_end_ns=85,
        validation_start_ns=24,
        validation_end_ns=119,
    )

    assert entry.train_end_ns > entry.validation_start_ns


@pytest.mark.trace("REQ-WP-022")
def test_a_walk_forward_span_that_ends_before_it_starts_is_still_refused() -> None:
    """The relaxation is about the two spans against each other, not about a
    span against itself."""
    with pytest.raises(ValueError, match="train"):
        registration(validation_regime="walk_forward", train_start_ns=90, train_end_ns=10)


@pytest.mark.trace("REQ-WP-022")
def test_the_validation_regime_has_no_default() -> None:
    """ADR-015's reasoning: a field with a default is a field an author can
    forget to think about, and this one decides which rule applies."""
    fields = {k: v for k, v in registration().__dict__.items() if k != "validation_regime"}

    with pytest.raises(TypeError, match="validation_regime"):
        Registration(**fields)


@pytest.mark.trace("REQ-WP-022")
def test_an_unknown_validation_regime_is_refused() -> None:
    with pytest.raises(ValueError, match="validation_regime"):
        registration(validation_regime="whatever_i_did")


@pytest.mark.trace("REQ-WP-022")
def test_a_span_that_ends_before_it_starts_is_refused() -> None:
    with pytest.raises(ValueError, match="train"):
        registration(train_start_ns=2_000, train_end_ns=1_000)


# --- the registry on the plane ----------------------------------------------


@pytest.fixture
def registry(catalog: Catalog) -> ModelRegistry:
    return ModelRegistry(catalog=catalog)


@pytest.mark.trace("REQ-WP-022")
def test_a_registration_reads_back_field_for_field(registry: ModelRegistry) -> None:
    entry = registration()

    registry.record([entry])

    assert registry.entries() == (entry,)


@pytest.mark.trace("REQ-WP-022")
def test_the_stored_hash_is_read_and_not_recomputed(registry: ModelRegistry) -> None:
    """A hash recomputed from a registration is a hash of the registration: it
    would pass every round-trip test while certifying nothing about the model.

    The registration here names an artifact the registry has never seen, and the
    hash still comes back exactly as written.
    """
    entry = registration(artifact_hash="c" * 64)

    registry.record([entry])

    assert registry.entries()[0].artifact_hash == "c" * 64


@pytest.mark.trace("REQ-WP-022")
def test_recording_one_registration_twice_stores_it_once(registry: ModelRegistry) -> None:
    """The plane is append-only and rejects nothing, so the writer has to
    (ADR-056)."""
    entry = registration()

    registry.record([entry])
    registry.record([entry])

    assert len(registry.entries()) == 1


@pytest.mark.trace("REQ-WP-022")
def test_the_registry_knows_which_artifacts_it_holds(registry: ModelRegistry) -> None:
    registry.record([registration(artifact_hash="d" * 64)])

    assert registry.holds("d" * 64)
    assert not registry.holds("e" * 64)


@pytest.mark.trace("REQ-WP-022")
def test_a_run_citing_a_registered_artifact_is_reportable(registry: ModelRegistry) -> None:
    """The point of the whole requirement: `UNRECORDED` becomes a hash that
    resolves to something."""
    registry.record([registration(artifact_hash="f" * 64)])
    identity = RunIdentity(
        dataset=dataset_reference({"bars": (1, "a" * 64)}),
        config=config_hash({"lookback": 60}),
        code=CodeVersion(commit="a" * 40, dirty=False),
        model_artifact="f" * 64,
    )

    identity.require_reproducible()
    require_registered(identity, models=registry)


@pytest.mark.trace("REQ-WP-022")
def test_a_run_citing_an_artifact_nobody_registered_is_refused(
    registry: ModelRegistry,
) -> None:
    """A hash nobody can resolve is a different kind of unreproducible from no
    hash at all, and a run that named a string would otherwise look checked."""
    identity = RunIdentity(
        dataset=dataset_reference({"bars": (1, "a" * 64)}),
        config=config_hash({"lookback": 60}),
        code=CodeVersion(commit="a" * 40, dirty=False),
        model_artifact="9" * 64,
    )

    with pytest.raises(NotReproducible, match="9" * 8):
        require_registered(identity, models=registry)


@pytest.mark.trace("REQ-WP-022")
def test_a_run_that_fitted_no_model_needs_no_registration(
    registry: ModelRegistry,
) -> None:
    """`NO_MODEL` is a run that never had an artifact. Requiring a registration
    for it would refuse every ablation and replay in the repository."""
    identity = RunIdentity(
        dataset=dataset_reference({"bars": (1, "a" * 64)}),
        config=config_hash({"lookback": 60}),
        code=CodeVersion(commit="a" * 40, dirty=False),
        model_artifact=ModelAbsence.NO_MODEL,
    )

    require_registered(identity, models=registry)


# --- what a comparison reports about what it fitted (REQ-WP-024) -------------


@pytest.mark.trace("REQ-WP-024")
def test_a_comparison_reports_the_artifact_of_the_model_it_fitted() -> None:
    """Under a name of its own.

    EXP-008's subject happens to share a name with one of its baselines, so a
    comparison that dropped the subject's artifact would still look complete --
    the baseline supplies one under the same name. This uses a distinct name so
    the subject has to answer for itself.
    """
    from channelflow.models import compare

    x, y = data()
    x_score, y_score = data(seed=7)

    report = compare(GradientBoostedTrees(), x_fit=x, y_fit=y, x_score=x_score, y_score=y_score)

    assert report.model.artifact
    assert all(score.artifact for score in report.baselines if score.ran)


@pytest.mark.trace("REQ-WP-024")
def test_a_comparison_handed_predictions_reports_no_artifact() -> None:
    """Two experiments supply their own probabilities. Reporting an artifact for
    a model that produced nothing would name a model that did no work."""
    from channelflow.models import compare

    x, y = data()
    x_score, y_score = data(seed=7)

    report = compare(
        GradientBoostedTrees(),
        x_fit=x,
        y_fit=y,
        x_score=x_score,
        y_score=y_score,
        model_predictions=np.full(len(y_score), 0.5),
    )

    assert report.model.artifact is None
