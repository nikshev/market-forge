"""One research run, end to end.

# @trace: REQ-WP-024

Five requirements built five mechanisms and nothing called any of them. A
`RunIdentity` was never assembled; [[REQ-BIAS-011]]'s field seam was never
reached from production code; nothing fitted a model and registered its
artifact; [[REQ-WP-023]]'s calibration per horizon had no caller. Each note
recorded the gap and answered it with "a caller will do it".

This is that caller, for [[REQ-EXP-008]]'s comparison.

**The refusals are the point.** Each mechanism refuses something -- a dirty
tree, an artifact nobody registered, a variant missing from its own field, a
horizon too thin to speak. Separately each refusal is theoretical. Assembled,
they decide whether a result may be reported at all, and a run that fails says
which component stopped it.

**Recording happens before refusing.** [[ADR-054]] made that unconditional: a
run over a dirty tree is recorded as unreproducible and *then* refused, because
declining to record it would leave no trace of a run that happened -- the
outcome PRD §41 rule 11 exists to prevent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from channelflow.dataset import CertifiedDataset
from channelflow.dataset.models import Row
from channelflow.experiments import (
    CodeVersion,
    ConfigValue,
    Field,
    Registry,
    Report,
    RunIdentity,
    config_hash,
    report_comparison,
)
from channelflow.lakehouse import ObjectStore
from channelflow.models import (
    ComparisonReport,
    HorizonCalibration,
    ModelRegistry,
    Registration,
    calibration_by_horizon,
    combined_artifact,
    require_registered,
)
from channelflow.turning.direct import DirectBaselineResult, Target, run_direct_baseline


class NothingScorable(ValueError):
    """No fold could be scored, so there is no run to report."""


@dataclass(frozen=True)
class StudyResult:
    """What one run produced, and everything needed to check it."""

    #: One identity per variant, each carrying all four of PRD §0 item 13's
    #: components.
    #: What the comparison found -- the per-fold reports and their aggregate.
    #: Returned rather than dropped: the identities say the run is citable and
    #: this says what it discovered, and a caller needs both.
    comparison: DirectBaselineResult
    identities: dict[str, RunIdentity]
    registrations: tuple[Registration, ...]
    #: The gate's report, or nothing when no variant beat the base rate. A model
    #: that cannot beat a base rate is not a model, so nothing is promoted --
    #: and the field is on record either way.
    report: Report | None
    reliability: HorizonCalibration
    scored_folds: int


@dataclass(frozen=True)
class _Compared:
    """The field, in the shape [[REQ-BIAS-011]]'s seam asks for."""

    compared: Field


def run_study(
    dataset: CertifiedDataset,
    *,
    store: ObjectStore,
    code: CodeVersion,
    experiment: str,
    target: Target,
    feature_names: tuple[str, ...],
    dataset_ref: str,
    as_of_ns: int,
    minimum_observations: int,
) -> StudyResult:
    """Run the comparison, register what it fitted, and report the field.

    `dataset_ref` and `code` are the caller's: nothing here reads a store for a
    dataset identity or shells out to git, which is [[REQ-REPRO-001]]'s FR-013
    inherited rather than restated.
    """
    result = run_direct_baseline(dataset, target=target, feature_names=feature_names)
    if not result.folds:
        raise NothingScorable(
            f"no fold of this dataset could score {target!r}: "
            + "; ".join(result.unscored)
            + ". A run with an empty field would go on record having measured nothing"
        )

    artifacts = _artifacts_per_variant(result.folds)
    models = ModelRegistry(store=store)
    registrations = tuple(
        _registration(
            variant=variant,
            artifact=artifact,
            code=code,
            feature_names=feature_names,
            target=target,
            result_folds=len(result.folds),
            rows=result.rows_scored,
            brier=_brier_of(result.folds, variant),
            spans=_spans(dataset),
        )
        for variant, artifact in sorted(artifacts.items())
    )
    models.record(registrations)

    variants: dict[str, Mapping[str, ConfigValue]] = {
        variant: {
            "variant": variant,
            "target": str(target),
            "features": list(feature_names),
            "folds": len(result.folds),
        }
        for variant in artifacts
    }
    field = Field(variants=variants, chosen=_winner(result.folds, artifacts))

    reported = report_comparison(
        _Compared(compared=field),
        experiment=experiment,
        dataset=dataset_ref,
        code=code,
        registry=Registry(store=store),
        model=dict(artifacts),
        as_of_ns=as_of_ns,
    )

    identities = {
        variant: RunIdentity(
            dataset=dataset_ref,
            config=config_hash(dict(variants[variant])),
            code=code,
            model_artifact=artifacts[variant],
        )
        for variant in artifacts
    }
    # After the gate, not before: the gate refuses an unreproducible run first,
    # and a caller fixing a dirty tree should not have to fix an artifact
    # complaint to discover it.
    #
    # Unreachable as this function stands -- it registered every artifact it is
    # about to cite, a few lines up -- and kept deliberately. It is what makes
    # [[REQ-WP-024]]'s FR-008 true for the next caller, which may register
    # somewhere else or not at all, and it costs a set lookup. A mutation that
    # deletes it survives the suite, and should: the guarantee is tested where
    # it lives, in `tests/unit/models/test_registry.py`.
    for identity in identities.values():
        require_registered(identity, models=models)

    return StudyResult(
        comparison=result,
        identities=identities,
        registrations=registrations,
        report=reported.report,
        reliability=_reliability(dataset, target=target, minimum_observations=minimum_observations),
        scored_folds=len(result.folds),
    )


def _artifacts_per_variant(folds: Sequence[ComparisonReport]) -> dict[str, str]:
    """One artifact per variant, over its folds in order.

    Deduplicated by name on purpose: a comparison scores its subject and its
    baselines, and for this experiment the subject *is* one of the baselines.
    Both are fitted the same way on the same data, so their artifacts agree and
    the field has one entry rather than a name twice -- which the gate would
    refuse, correctly.
    """
    per_variant: dict[str, list[str]] = {}
    for report in folds:
        # One artifact per variant per fold. A variant that appears twice in a
        # fold -- as the subject and as a baseline of the same name -- was
        # fitted identically both times, so counting it twice would give it a
        # longer artifact than its rivals for no reason anyone could read.
        seen: set[str] = set()
        for score in (report.model, *report.baselines):
            if score.artifact is None or score.name in seen:
                continue
            seen.add(score.name)
            per_variant.setdefault(score.name, []).append(score.artifact)
    return {name: combined_artifact(parts) for name, parts in per_variant.items()}


def _brier_of(folds: Sequence[ComparisonReport], variant: str) -> float | None:
    """A variant's rows-weighted Brier over the folds that scored it."""
    weighted = 0.0
    rows = 0
    for report in folds:
        for score in (report.model, *report.baselines):
            if score.name != variant or score.brier is None or score.artifact is None:
                continue
            weighted += score.brier * report.rows_scored
            rows += report.rows_scored
    return weighted / rows if rows else None


def _winner(folds: Sequence[ComparisonReport], artifacts: Mapping[str, str]) -> str | None:
    """The lowest Brier, and only if it beat the base rate.

    `None` otherwise, which is a promotion that did not happen rather than a
    field with no best member. A model that cannot beat a base rate is not a
    model -- PRD §23.6's own argument, and §45's Phase 7 acceptance turns on it.
    """
    scored = {
        variant: brier for variant in artifacts if (brier := _brier_of(folds, variant)) is not None
    }
    base = scored.get("no_skill_base_rate")
    if not scored or base is None:
        return None
    # Ties broken by name, so one dataset gives one answer.
    best = min(scored, key=lambda variant: (scored[variant], variant))
    return None if scored[best] >= base else best


@dataclass(frozen=True)
class _Spans:
    """The outer extent of what a run trained and validated on."""

    train_start_ns: int
    train_end_ns: int
    validation_start_ns: int
    validation_end_ns: int


def _spans(dataset: CertifiedDataset) -> _Spans:
    """The true extent of the folds, over every row they hold.

    These overlap, and that is correct rather than tolerated: walk-forward folds
    interleave by construction -- fold 1 trains on data later than fold 0
    validated on. Within a fold they never touch, which is the property that
    matters and the one `WalkForwardFolds` and the leakage certificate enforce.

    Written after [[ADR-058]]. Before it these four fields held 1/2/2/3, because
    `Registration` refused any overlap and a walk-forward run cannot satisfy
    that -- so a registry whose whole job is describing an artifact truthfully
    carried four invented numbers.
    """
    train = [row.as_of_ns for fold in dataset.folds for row in fold.train]
    validate = [row.as_of_ns for fold in dataset.folds for row in fold.validate]
    return _Spans(
        train_start_ns=min(train),
        train_end_ns=max(train),
        validation_start_ns=min(validate),
        validation_end_ns=max(validate),
    )


def _registration(
    *,
    variant: str,
    artifact: str,
    code: CodeVersion,
    feature_names: tuple[str, ...],
    target: Target,
    result_folds: int,
    rows: int,
    brier: float | None,
    spans: _Spans,
) -> Registration:
    """PRD §23.9's eleven fields for one variant of this run."""
    return Registration(
        model_type=variant,
        feature_set_versions={name: 1 for name in feature_names},
        train_start_ns=spans.train_start_ns,
        train_end_ns=spans.train_end_ns,
        validation_start_ns=spans.validation_start_ns,
        validation_end_ns=spans.validation_end_ns,
        code_commit=code.commit,
        hyperparameters={"target": str(target), "folds": result_folds},
        scaler_parameters={"none": "features are used as given"},
        calibration_model="none",
        metrics={"brier": brier if brier is not None else float("nan"), "rows": float(rows)},
        artifact_hash=artifact,
        deployment_status="shadow",
        # The folds this run used are walk-forward, and saying so is what lets
        # the spans above be true ([[ADR-058]]).
        validation_regime="walk_forward",
    )


def _reliability(
    dataset: CertifiedDataset, *, target: Target, minimum_observations: int
) -> HorizonCalibration:
    """Reliability at each horizon over the rows the folds validated on.

    The base rate is used as the prediction because that is the number every
    other variant has to beat, and a reliability curve for the thing being
    beaten is the one a reader can anchor on.
    """
    rows: list[Row] = [row for fold in dataset.folds for row in fold.validate]
    share = sum(1.0 for row in rows if row.label.label_class == target) / max(len(rows), 1)
    return calibration_by_horizon(
        rows,
        np.full(len(rows), share, dtype=np.float64),
        target=str(target),
        minimum_observations=minimum_observations,
    )
