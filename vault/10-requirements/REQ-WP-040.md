---
id: REQ-WP-040
title: A registration names the dataset it was trained on
type: work-package
prd_ref: "§0 item 13, §23.9"
prd_lines: "27, 4137-4151"
phase: 7
status: implemented
depends_on: [REQ-WP-022, REQ-WP-039]
tags: []
---

## Requirement

PRD §0 item 13 is a governing principle:

    Усі результати backtest/research повинні відтворюватися з versioned dataset
    + config + code commit hash + model artifact hash.

    (Every backtest/research result must be reproducible from a versioned
    dataset + config + code commit hash + model artifact hash.)

PRD §23.9 lists what a model artifact includes:

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

**Four things are required and three are recorded.** The code commit is there,
the artifact hash is there, and the hyperparameters and scaler parameters are
the config. The versioned dataset — the first of the four, and the one the other
three are meaningless without — has no field.

A registration is therefore reproducible in the sense that you can rebuild the
model, and not in the sense that you can rebuild the *result*: the same code and
the same weights over a different slice of history produce a different number,
and nothing recorded would say which slice it was.

This is not a hypothetical. [[REQ-WP-038]] built retention, which expires
snapshots by age and keeps the ones a lineage names — and there is no lineage to
read, so a caller must supply pins by hand or prune without them. The gap has a
consumer waiting for it.

**Precedent**: [[ADR-058]] already added a twelfth field to §23.9's eleven, when
§41 rule 10 demanded something the list did not carry. The list describes the
artifact; §0 governs.

## Acceptance

- A registration names the dataset it was trained on: which table, which
  snapshot, and that snapshot's content hash.
- The content hash is recorded, not merely the snapshot id: an id is a name and
  a hash is a claim about what was under it ([[ADR-053]]).
- A registration whose dataset no longer resolves is detectable — the run is
  still recorded, and a reader can tell that its dataset is gone.
- Retention can read pins from the registry rather than being handed them.
- A registration with no dataset is refused, for the reason [[ADR-015]] gives
  about defaults: a field with one is a field an author can forget to think
  about, and this one selects whether a result is checkable.
- Existing registrations' other eleven fields are unchanged.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-078-dataset-lineage]]
- **Tests:**
    - `tests/unit/models/test_dataset_lineage.py::test_a_citation_by_name_without_a_claim_is_refused`
    - `tests/unit/models/test_dataset_lineage.py::test_a_dataset_that_is_still_there_resolves`
    - `tests/unit/models/test_dataset_lineage.py::test_a_registered_snapshot_survives_a_pass_that_would_have_expired_it`
    - `tests/unit/models/test_dataset_lineage.py::test_a_registration_without_a_dataset_is_refused`
    - `tests/unit/models/test_dataset_lineage.py::test_a_registry_holding_nothing_for_a_table_pins_nothing`
    - `tests/unit/models/test_dataset_lineage.py::test_a_snapshot_retention_expired_resolves_as_gone`
    - `tests/unit/models/test_dataset_lineage.py::test_a_snapshot_that_now_holds_something_else_is_not_the_same_dataset`
    - `tests/unit/models/test_dataset_lineage.py::test_an_origin_can_name_an_earlier_snapshot`
    - `tests/unit/models/test_dataset_lineage.py::test_an_origin_carries_the_table_the_snapshot_and_the_hash`
    - `tests/unit/models/test_dataset_lineage.py::test_an_origin_with_no_table_is_refused`
    - `tests/unit/models/test_dataset_lineage.py::test_an_unresolvable_dataset_does_not_stop_the_registration_being_read`
    - `tests/unit/models/test_dataset_lineage.py::test_pins_are_the_snapshots_registrations_name`
    - `tests/unit/models/test_dataset_lineage.py::test_pins_for_one_table_are_not_pins_for_another`
    - `tests/unit/models/test_dataset_lineage.py::test_the_same_rows_give_the_same_citation`
    - `tests/unit/models/test_dataset_lineage.py::test_two_registrations_over_one_snapshot_are_one_pin`
- **Code:**
    - `src/channelflow/models/registry.py`
- **Outcomes:** [[OUT-2026-09-11-implement-dataset-lineage]], [[OUT-2026-09-11-requirement-dataset-lineage]], [[OUT-2026-09-11-spec-plan-dataset-lineage]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Found while extracting [[REQ-WP-038]]: retention needed a lineage to honour and
there was none. Recorded then as its own work rather than designed around, and
this is that work.

The narrower question this does **not** answer: whether a *study* — a
walk-forward run over many folds — cites one dataset or one per fold. Today a
run reads one table at one snapshot, so one is right; a study over several
tables would need more, and nothing does that yet.
