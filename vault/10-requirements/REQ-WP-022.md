---
id: REQ-WP-022
title: A fitted model is registered, hashed and citable
type: work-package
prd_ref: "§23.9, §0 item 13, §29.B"
prd_lines: "4138-4150"
phase: 7
status: implemented
depends_on: [REQ-WP-018, REQ-REPRO-001, REQ-STORE-001]
tags: []
---

## Requirement

PRD §23.9, in full:

    ## 23.9. Model registry

    Model artifact includes:

    - model type;
    - feature set versions;
    - train start/end;
    - validation start/end;
    - code commit;
    - hyperparameters;
    - scaler parameters;
    - calibration model;
    - metrics;
    - artifact hash;
    - deployment status.

Unlike Phase 0's event bus and Phase 1's market metadata, this deliverable is
specified: eleven fields, named.

**Why it matters beyond the list.** PRD §0 item 13 requires every research
result to be reproducible from four things, and the fourth is a model artifact
hash. [[REQ-REPRO-001]] built the machinery for all four and this is the one
nothing fills: `ModelArtifact` appears nowhere outside `channelflow.experiments`,
so every run that fitted a model records `UNRECORDED` — the value whose whole
job is to say the run cannot be reproduced.

Models are constructed by callers, fitted in place, and discarded. Two runs of
one experiment on one dataset produce two models nothing can tell apart, and a
result quoting one of them cites a thing that no longer exists.

## Acceptance

- an artifact hash is derived from a fitted model's own parameters, so two
  models fitted alike hash alike and two that differ do not;
- an unfitted model has no artifact hash, and that is distinguishable from a
  hash of nothing;
- a registration carries all eleven of §23.9's fields, with none defaulted
  silently;
- a registration is stored on the canonical plane and read back identically;
- registering the same artifact twice does not store it twice;
- a run's `model_artifact` can be a registered hash instead of `UNRECORDED`, and
  a run citing an unregistered hash is refused;
- nothing that exists today changes what it computes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-061-model-registry]]
- **Tests:**
    - `tests/unit/models/test_registry.py::test_a_difference_below_printing_precision_changes_the_hash`
    - `tests/unit/models/test_registry.py::test_a_hyperparameter_alone_changes_the_hash`
    - `tests/unit/models/test_registry.py::test_a_model_fitted_on_other_data_hashes_differently`
    - `tests/unit/models/test_registry.py::test_a_registration_carries_every_field_section_23_9_names`
    - `tests/unit/models/test_registry.py::test_a_registration_reads_back_field_for_field`
    - `tests/unit/models/test_registry.py::test_a_registration_with_no_metrics_is_refused`
    - `tests/unit/models/test_registry.py::test_a_run_citing_a_registered_artifact_is_reportable`
    - `tests/unit/models/test_registry.py::test_a_run_citing_an_artifact_nobody_registered_is_refused`
    - `tests/unit/models/test_registry.py::test_a_run_that_fitted_no_model_needs_no_registration`
    - `tests/unit/models/test_registry.py::test_a_span_that_ends_before_it_starts_is_refused`
    - `tests/unit/models/test_registry.py::test_a_validation_span_overlapping_the_training_span_is_refused`
    - `tests/unit/models/test_registry.py::test_an_array_reshaped_without_changing_a_byte_changes_the_hash`
    - `tests/unit/models/test_registry.py::test_an_empty_named_field_is_refused[calibration_model]`
    - `tests/unit/models/test_registry.py::test_an_empty_named_field_is_refused[code_commit]`
    - `tests/unit/models/test_registry.py::test_an_empty_named_field_is_refused[deployment_status]`
    - `tests/unit/models/test_registry.py::test_an_empty_named_field_is_refused[model_type]`
    - `tests/unit/models/test_registry.py::test_an_unfitted_model_is_refused_rather_than_hashed`
    - `tests/unit/models/test_registry.py::test_every_model_type_can_say_whether_it_is_fitted`
    - `tests/unit/models/test_registry.py::test_recording_one_registration_twice_stores_it_once`
    - `tests/unit/models/test_registry.py::test_the_hash_is_framed_so_fields_cannot_borrow_from_each_other`
    - `tests/unit/models/test_registry.py::test_the_registry_knows_which_artifacts_it_holds`
    - `tests/unit/models/test_registry.py::test_the_stored_hash_is_read_and_not_recomputed`
    - `tests/unit/models/test_registry.py::test_two_identical_fits_hash_alike`
    - `tests/unit/models/test_registry.py::test_two_models_with_one_hyperparameter_apart_hash_differently`
    - `tests/unit/models/test_registry.py::test_two_states_that_concatenate_alike_do_not_hash_alike`
- **Outcomes:** [[OUT-2026-09-10-implement-model-registry]], [[OUT-2026-09-10-plan-model-registry]], [[OUT-2026-09-10-requirement-model-registry]], [[OUT-2026-09-10-spec-model-registry]]
<!-- trace:end -->

## Notes

This is the fourth of PRD §0 item 13's four hashes, and the last one with no
producer. [[ADR-054]] put both §0.13 and §41 rule 11 behind the same gate, and
that gate has been refusing on this component since it was written — correctly,
because a model that was fitted and not recorded is a run nobody can repeat.

**Deployment status is recorded, not acted on.** §23.9 names it and PRD §45's
Phase 7 acceptance turns promotion on a GMDH beating its baseline out of sample.
Deciding promotion is [[REQ-EXP-008]]'s and the gate's; this stores what was
decided.

**Serving the registry over the API is not in scope**, and it is worth saying
which pattern that is not: the registry's consumer is the experiment registry,
which cites an artifact hash the moment one exists. That is a real consumer in
the same repository, not a promise of one.
