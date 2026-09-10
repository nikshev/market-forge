---
id: REQ-WP-024
title: One research run produces a result that is reproducible and reportable
type: work-package
prd_ref: "§0 item 13, §23.5A, §23.9, §41 rule 11"
prd_lines: "27, 4065-4074, 4138-4150, 5327"
phase: null
status: implemented
depends_on: [REQ-REPRO-001, REQ-BIAS-011, REQ-WP-022, REQ-WP-023, REQ-US-007]
tags: []
---

## Requirement

PRD §0 item 13 asks for a research result reproducible from four things. Five
requirements built the parts and **none of them is called by anything**:

- [[REQ-REPRO-001]] built run identity, the registry and the gate — nothing
  assembles a `RunIdentity`;
- [[REQ-BIAS-011]] built the seam that puts a field on record — nothing reaches
  it from production code;
- [[REQ-WP-022]] built the artifact hash and the model registry — nothing fits
  and registers a model in one path;
- [[REQ-WP-023]] built calibration per horizon — nothing calls it;
- [[REQ-PIPE-001]] produces the dataset reference the first hash needs.

Each of those notes recorded the same gap in its own words, and each time the
answer was "a caller will do it". This is the caller.

**One run, end to end.** Given a certified dataset, a store and a code version:
fit the models a comparison compares, register what was fitted, assemble each
variant's identity from all four hashes, put the whole field on record, publish
the winner through the gate, and report reliability at each horizon.

**Why this is a requirement rather than glue.** Every one of the five mechanisms
refuses something. Assembled, they refuse together: a dirty tree, an unregistered
artifact, a variant missing from the field, a horizon too thin to speak. A run
that survives all of them is reproducible in the sense §0 item 13 means, and one
that does not says which component stopped it. Until they are assembled, each
refusal is theoretical.

## Acceptance

- a run fits the models a comparison compares and registers each variant's
  artifact, so the fourth hash resolves to a registration rather than reading
  `UNRECORDED`;
- every variant compared is on record before any winner is published, whatever
  its outcome;
- a run over a dirty working tree is refused, and says so;
- a run citing an artifact nobody registered is refused, and says which;
- the result carries calibration at each horizon the dataset actually contains,
  and a thin horizon says so rather than showing a curve;
- two runs over one dataset with one code version produce identical run hashes;
- nothing an existing experiment computes changes.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-063-research-run]]
- **Tests:**
    - `tests/unit/experiments/test_fields.py::test_each_variant_can_carry_its_own_model_artifact`
    - `tests/unit/models/test_registry.py::test_a_comparison_handed_predictions_reports_no_artifact`
    - `tests/unit/models/test_registry.py::test_a_comparison_reports_the_artifact_of_the_model_it_fitted`
    - `tests/unit/models/test_registry.py::test_a_variant_s_artifact_covers_every_fold_and_their_order`
    - `tests/unit/models/test_registry.py::test_a_variant_with_no_scored_fold_has_no_artifact`
    - `tests/unit/pipeline/test_study.py::test_a_dataset_with_nothing_scorable_is_refused`
    - `tests/unit/pipeline/test_study.py::test_a_dirty_run_is_still_recorded_before_it_is_refused`
    - `tests/unit/pipeline/test_study.py::test_a_dirty_tree_stops_the_report_and_says_so`
    - `tests/unit/pipeline/test_study.py::test_a_thin_horizon_says_so_rather_than_showing_a_curve`
    - `tests/unit/pipeline/test_study.py::test_a_variant_s_artifact_covers_its_folds_rather_than_one_of_them`
    - `tests/unit/pipeline/test_study.py::test_a_variant_that_lost_is_on_record_too`
    - `tests/unit/pipeline/test_study.py::test_a_winner_is_published_only_when_something_beat_the_base_rate`
    - `tests/unit/pipeline/test_study.py::test_an_artifact_only_resolves_against_the_registry_that_holds_it`
    - `tests/unit/pipeline/test_study.py::test_every_variant_is_registered_and_on_record`
    - `tests/unit/pipeline/test_study.py::test_reliability_is_reported_at_each_horizon`
    - `tests/unit/pipeline/test_study.py::test_the_fourth_hash_resolves_instead_of_reading_unrecorded`
    - `tests/unit/pipeline/test_study.py::test_the_registration_carries_the_run_s_real_spans`
    - `tests/unit/pipeline/test_study.py::test_two_runs_over_one_dataset_produce_equal_identities`
- **Code:**
    - `src/channelflow/pipeline/study.py`
- **Outcomes:** [[OUT-2026-09-10-fix-validation-regime]], [[OUT-2026-09-10-implement-research-run]], [[OUT-2026-09-10-plan-research-run]], [[OUT-2026-09-10-requirement-research-run]], [[OUT-2026-09-10-spec-research-run]]
<!-- trace:end -->

## Notes

Extracted by hand from the open questions of five requirements rather than from
a PRD section, because the gap is between them rather than in any one. The PRD
references above are what each part serves.

**One artifact per variant, not per fold.** A variant is fitted once per fold, so
there are several fitted models behind one comparison. What a result cites is the
variant *as run* — the whole set of folds — so the artifact hash covers them
together. Registering each fold separately would produce artifacts nothing cites
and leave the run's own identity ambiguous.

**Which experiment is wired is deliberately one.** [[REQ-EXP-008]]'s baseline
comparison is the one PRD §45's Phase 7 acceptance turns on. A second is a second
caller of the same path, not a change to it — and if it turns out to be a change,
that is a finding about the path.
