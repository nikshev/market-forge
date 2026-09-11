---
id: REQ-WP-038
title: Retention expires data by policy, and never what a lineage still names
type: work-package
prd_ref: "§6.4.9, §45 Phase 8"
prd_lines: "733-743, 6909"
phase: 8
status: implemented
depends_on: [REQ-STORE-001, REQ-WP-037]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "S3 cold retention;" and §6.4.9 gives the shape:

    ### 6.4.9. Retention tiers

    Retention must be configurable per event family. Suggested semantics, not
    hard-coded durations:

    - **Tier A / Pinot HOT:** enough history for live dashboards, feature
      windows and alert drill-down;
    - **Tier B / Iceberg normalized:** full research history;
    - **Tier C / raw archive:** source-of-truth payloads where re-normalization
      may be required;
    - **Tier D / derived research artifacts:** retained by experiment/model
      lineage policy.

    Do not retain full-depth order-book deltas indefinitely in Pinot solely
    because they exist. Pinot should contain the subset needed for HOT queries;
    full history belongs in object storage/Iceberg.

**"Suggested semantics, not hard-coded durations" is the requirement's first
line.** The PRD declines to name a number, so nothing here may name one either:
every duration is an argument, and a default written into the code would be a
research default wearing a decision's clothes (§13.11's warning, applied where
the PRD has already applied it itself).

**Tier D is the one with teeth.** "Retained by experiment/model lineage policy"
means retention is not a function of age alone: a snapshot an experiment's
lineage names must survive however old it is. §0 item 13 asks a result to be
reproducible from "a versioned dataset + config + code commit hash + model
artifact hash", and a retention pass that expired the versioned dataset would
destroy that reproducibility silently — the model would still load, the config
would still read, and the run would simply stop being checkable.

**Deleting is a capability, not an operation.** The canonical plane is
append-only (§0.5) and `ObjectStore` deliberately exposes no `delete`; the table
layer must never have one. Retention needs it. The capability therefore has to
be expressed so that the code that prunes can have it and the code that commits
cannot, rather than added to the port everything shares.

## Acceptance

- Every retention duration is an argument; no duration is written into the code.
- A snapshot named as pinned is never expired, whatever its age.
- Expiring a snapshot never leaves a manifest naming an absent file: the pruning
  order is the inverse of the writing order.
- The newest snapshot is never expired, whatever the policy says, because a
  table with no readable current state is not a retained table.
- A pruned table still reads, and still reads at every snapshot that survived.
- What was expired is reported, including what was kept and why.
- The ability to delete is available to retention and not to the table layer.
- Verified against a real object store in CI, as [[REQ-WP-037]]'s round trip is.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-076-retention]]
- **Tests:**
    - `tests/unit/lakehouse/test_retention.py::test_a_pin_naming_a_snapshot_that_does_not_exist_is_refused`
    - `tests/unit/lakehouse/test_retention.py::test_a_pinned_snapshot_survives_and_still_reads`
    - `tests/unit/lakehouse/test_retention.py::test_a_pruned_table_still_reads_and_verifies`
    - `tests/unit/lakehouse/test_retention.py::test_a_refused_pin_removes_nothing`
    - `tests/unit/lakehouse/test_retention.py::test_a_surviving_snapshot_keeps_its_name`
    - `tests/unit/lakehouse/test_retention.py::test_a_table_nobody_wrote_to_is_left_alone`
    - `tests/unit/lakehouse/test_retention.py::test_a_table_that_can_never_be_pruned_says_so_before_it_says_anything_else`
    - `tests/unit/lakehouse/test_retention.py::test_a_table_with_no_event_time_has_no_notion_of_old`
    - `tests/unit/lakehouse/test_retention.py::test_only_retention_deletes`
    - `tests/unit/lakehouse/test_retention.py::test_rows_older_than_the_policy_go_and_the_rest_stay`
    - `tests/unit/lakehouse/test_retention.py::test_running_twice_removes_nothing_more`
    - `tests/unit/lakehouse/test_retention.py::test_the_newest_snapshot_survives_any_policy`
    - `tests/unit/lakehouse/test_retention.py::test_the_pass_actually_frees_bytes`
    - `tests/unit/lakehouse/test_retention.py::test_the_policy_has_no_default_duration`
    - `tests/unit/lakehouse/test_retention.py::test_the_report_names_the_cutoff_it_used`
    - `tests/unit/lakehouse/test_retention.py::test_the_report_says_why_each_survivor_survived`
    - `tests/unit/lakehouse/test_retention.py::test_the_rule_guards_the_irreversible_step_and_not_the_other_one`
    - `tests/unit/lakehouse/test_retention.py::test_two_policies_over_one_table_keep_different_amounts`
- **Code:**
    - `src/channelflow/lakehouse/retention.py`
- **Outcomes:** [[OUT-2026-09-11-implement-retention]], [[OUT-2026-09-11-plan-retention-resumed]], [[OUT-2026-09-11-requirement-retention]], [[OUT-2026-09-11-spec-retention]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

**Tiers A and C describe stores that do not exist here.** Tier A is Pinot,
deferred by [[ADR-002]] until a HOT serving requirement exists; Tier C is a raw
archive that nothing writes. Retention over them is not deferred work hiding in
this requirement — there is nothing to retain. Tier B is the canonical plane and
Tier D is its research artifacts, and those two are this requirement's.

**Nothing produces the pinned set.** `Registration` records eleven of §23.9's
fields and does not record which dataset snapshot a model was trained on, so
§0 item 13's "versioned dataset" has no home in the registry today. Retention
therefore takes the pinned snapshots as an argument and the gap is named here
rather than designed around: the day something records lineage, retention reads
it, and until then a caller pruning without pins is doing so knowingly.
