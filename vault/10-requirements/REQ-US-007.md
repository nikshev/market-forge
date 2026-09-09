---
id: REQ-US-007
title: Train ML/GMDH only on point-in-time features
type: user-story
prd_ref: "US-007 — Train ML/GMDH only on point-in-time features"
prd_lines: "281-286"
phase: null
status: implemented
depends_on: ["REQ-WP-017", "REQ-WP-018"]
tags: []
---

## Requirement

As a researcher, I want a guarantee that the training dataset contains no feature leakage.

## Acceptance

- the training dataset passes leakage assertions before being used for ML/GMDH training.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-031-training-gate]]
- **Tests:**
    - `tests/unit/dataset/test_training_gate.py::test_a_bare_fold_list_is_refused_by_training`
    - `tests/unit/dataset/test_training_gate.py::test_a_certificate_cannot_be_built_around_an_unclean_report`
    - `tests/unit/dataset/test_training_gate.py::test_a_clean_dataset_certifies`
    - `tests/unit/dataset/test_training_gate.py::test_a_leaked_label_refuses_and_names_the_rule`
    - `tests/unit/dataset/test_training_gate.py::test_an_empty_dataset_refuses`
    - `tests/unit/dataset/test_training_gate.py::test_certifying_twice_gives_equal_certificates`
    - `tests/unit/dataset/test_training_gate.py::test_clean_rows_do_not_certify_contaminated_folds`
    - `tests/unit/dataset/test_training_gate.py::test_every_training_entry_point_requires_a_certificate`
    - `tests/unit/dataset/test_training_gate.py::test_training_reads_its_folds_from_the_certificate`
- **Code:**
    - `src/channelflow/dataset/__init__.py`
    - `src/channelflow/dataset/certified.py`
    - `src/channelflow/research/ablation.py`
    - `src/channelflow/turning/direct.py`
    - `src/channelflow/turning/experiment.py`
- **Outcomes:** [[OUT-2026-09-09-implement-training-gate]], [[OUT-2026-09-09-plan-training-gate]], [[OUT-2026-09-09-spec-training-gate]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
