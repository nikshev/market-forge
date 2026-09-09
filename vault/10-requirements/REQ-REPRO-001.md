---
id: REQ-REPRO-001
title: Run identity, the experiment registry, and the reporting gate
type: work-package
prd_ref: "§0 item 13, §41 rule 11, §29.B canonical tables, §30 experiments"
prd_lines: "27, 5327, 4579-4602, 4681-4694"
phase: null
status: implemented
depends_on: ["REQ-STORE-001", "REQ-WP-017"]
tags: []
hard_gated: false
---

## Requirement

PRD §0 item 13:

> Усі результати backtest/research повинні відтворюватися з versioned dataset +
> config + code commit hash + model artifact hash.

("All backtest/research results must be reproducible from a versioned dataset +
config + code commit hash + model artifact hash." Restated by
[[REQ-PRIN-013]].)

PRD §41 rule 11, restated by [[REQ-BIAS-011]]:

> Store all discarded experiment variants to reduce silent cherry-picking.

PRD §29.B lists `backtest_runs` and `experiment_membership` among the canonical
tables, and ends:

> Every research-grade table must support dataset lineage/snapshot
> reproducibility.

PRD §30 lists `experiments` and `backtest_runs` metadata among the PostgreSQL
tables.

PRD §45's Phase 6 names two deliverables nothing provides: **experiment
registry** and **dataset hashes**.

[[ADR-024]] recorded why rule 11 had no home: "experiment tracking, which
nothing here does". [[ADR-053]] built the first of the four hashes — a
lakehouse snapshot's content hash. This requirement is the other three, the
registry that holds them, and the gate that makes them mean something.

## Acceptance

Run identity (§0 item 13):

- a run's identity carries all four components — dataset, config, code commit,
  model artifact — and each is present or explicitly absent, never merely
  missing;
- a run that fits no model and a run whose model artifact nobody recorded are
  distinguishable, and only the second is irreproducible;
- a code commit taken from a dirty working tree names a tree that does not
  exist, and a run carrying one is irreproducible;
- the same four components produce the same run hash in any process; any change
  to any of them changes it.

Dataset composition (§29.B):

- a run that reads several tables composes their snapshot identities into one
  dataset component, independent of the order the tables were listed in;
- a dataset component names the snapshot each table was read at, so the run can
  be replayed against the same bytes.

Config hashing (§31):

- a configuration hashes deterministically across processes, independent of key
  order;
- two configurations that differ anywhere hash differently, including where they
  differ only in a value's type.

The registry (§29.B, §41 rule 11):

- every run is recorded, whether its result was kept or discarded;
- the registry is append-only and its history is immutable;
- a recorded run can be read back with its identity and its outcome intact.

The reporting gate (§0 item 13, §41 rule 11):

- a result whose run is irreproducible cannot be reported, and the refusal names
  which of the four components is missing;
- a winner cannot be reported without naming the field it was chosen from, and
  every variant in that field must already be in the registry — so discarding a
  variant silently and reporting the survivor is refused rather than trusted.

## Scope

**In:** the four-component run identity and its hash, the dirty-tree guard,
config hashing, dataset composition over lakehouse snapshots, the registry table
on the canonical plane, and the reporting gate.

**Out, and named rather than silently dropped:**

- **Reading the git commit.** A library that shells out to `git` is a library
  that cannot be tested and that behaves differently inside a container. The
  commit and the dirty flag are supplied by the caller; a thin adapter may read
  them, and the core takes them as data.
- **Computing a model artifact's hash.** A model artifact is a file whose format
  belongs to whatever produced it. The registry takes the hash and refuses to
  invent one.
- **The PostgreSQL `experiments` table (§30).** [[ADR-002]] made object storage
  the canonical plane and §29.B lists these tables there; a second copy in
  Postgres is a control-plane question, not a lineage one.
- **Automatic registration.** Nothing walks the seventeen research modules and
  registers their runs. Each experiment adopts the registry as its own step.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-053-experiment-registry]]
- **Tests:**
    - `tests/unit/experiments/test_hashing.py::test_a_config_hashes_the_same_however_it_was_written_down`
    - `tests/unit/experiments/test_hashing.py::test_a_config_holding_something_unencodable_is_refused`
    - `tests/unit/experiments/test_hashing.py::test_a_config_that_differs_anywhere_hashes_differently`
    - `tests/unit/experiments/test_hashing.py::test_a_dataset_reference_changes_with_the_snapshot_and_with_the_content`
    - `tests/unit/experiments/test_hashing.py::test_a_dataset_reference_does_not_depend_on_the_order_of_its_tables`
    - `tests/unit/experiments/test_hashing.py::test_a_dataset_reference_over_no_tables_is_refused`
    - `tests/unit/experiments/test_hashing.py::test_a_list_keeps_its_order`
    - `tests/unit/experiments/test_hashing.py::test_a_non_string_key_is_refused`
    - `tests/unit/experiments/test_hashing.py::test_a_null_is_a_value_and_not_an_absence`
    - `tests/unit/experiments/test_hashing.py::test_a_number_written_as_a_string_is_not_the_same_config`
    - `tests/unit/experiments/test_hashing.py::test_a_quoted_flag_is_not_the_same_config_as_an_unquoted_one`
    - `tests/unit/experiments/test_hashing.py::test_a_table_referenced_at_snapshot_zero_is_refused`
    - `tests/unit/experiments/test_hashing.py::test_a_table_referenced_without_a_content_hash_is_refused`
    - `tests/unit/experiments/test_hashing.py::test_nesting_cannot_be_flattened_away`
    - `tests/unit/experiments/test_identity.py::test_a_commit_from_a_dirty_tree_is_not_reproducible`
    - `tests/unit/experiments/test_identity.py::test_a_component_cannot_borrow_a_character_from_the_next_one`
    - `tests/unit/experiments/test_identity.py::test_a_dirty_run_is_not_the_same_run_as_its_commit`
    - `tests/unit/experiments/test_identity.py::test_a_model_whose_artifact_nobody_recorded_is_not_reproducible`
    - `tests/unit/experiments/test_identity.py::test_a_run_that_fits_no_model_is_still_reproducible`
    - `tests/unit/experiments/test_identity.py::test_a_run_with_all_four_components_is_reproducible`
    - `tests/unit/experiments/test_identity.py::test_a_run_with_no_dataset_or_no_config_is_refused_outright`
    - `tests/unit/experiments/test_identity.py::test_an_abbreviated_or_invented_commit_is_refused`
    - `tests/unit/experiments/test_identity.py::test_changing_any_component_changes_the_run_hash`
    - `tests/unit/experiments/test_identity.py::test_every_missing_component_is_named_at_once`
    - `tests/unit/experiments/test_identity.py::test_the_same_four_components_give_the_same_run_hash`
    - `tests/unit/experiments/test_registry.py::test_a_recorded_run_reads_back_with_its_identity_intact`
    - `tests/unit/experiments/test_registry.py::test_a_run_without_a_variant_name_is_refused`
    - `tests/unit/experiments/test_registry.py::test_an_absence_reads_back_as_an_absence`
    - `tests/unit/experiments/test_registry.py::test_an_unreproducible_run_is_recorded_rather_than_refused`
    - `tests/unit/experiments/test_registry.py::test_nothing_in_the_experiments_package_consults_a_clock`
    - `tests/unit/experiments/test_registry.py::test_nothing_in_the_experiments_package_shells_out_to_git`
    - `tests/unit/experiments/test_registry.py::test_recording_nothing_is_refused`
    - `tests/unit/experiments/test_registry.py::test_the_registry_table_can_answer_a_point_in_time_read`
    - `tests/unit/experiments/test_report.py::test_a_report_carries_the_three_hashes_a_reader_needs`
    - `tests/unit/experiments/test_report.py::test_a_reproducible_winner_with_its_whole_field_on_record_is_published`
    - `tests/unit/experiments/test_report.py::test_an_irreproducible_result_cannot_be_reported`
    - `tests/unit/experiments/test_report.py::test_an_unrecorded_model_artifact_stops_a_report_too`
- **Code:**
    - `src/channelflow/experiments/__init__.py`
    - `src/channelflow/experiments/hashing.py`
    - `src/channelflow/experiments/identity.py`
    - `src/channelflow/experiments/registry.py`
    - `src/channelflow/experiments/report.py`
- **Outcomes:** [[OUT-2026-09-09-implement-experiment-registry]], [[OUT-2026-09-09-plan-experiment-registry]], [[OUT-2026-09-09-requirement-experiment-registry]], [[OUT-2026-09-09-spec-experiment-registry]]
<!-- trace:end -->

## Notes

Hand-written: PRD §46 has no work package for §0 item 13 or §41 rule 11, and
`tools/extract_prd.py` does not read §29 or §30. The acceptance criteria are
derived where the PRD states a property rather than a test, and quoted where it
states them outright. This section is human territory and is never
machine-rewritten.
