---
description: "Task list for REQ-WP-017 and six REQ-BIAS-* constraints"
---

# Tasks: Point-in-time dataset

**Tests**: Written first. Every leakage check gets a test that constructs the
violation — a check nobody has seen fail is a check nobody knows works.

## Phase 1: The as-of join (US1)

- [ ] T001 Write failing `test_join.py`: only snapshots at or before `t`; the most recent of several; PRD §24.1's invariant refused; no snapshot means the row is dropped and counted, never forward-filled; a feature from an unfinalized bar refused (SC-001, SC-002). Markers for `REQ-WP-017` and `REQ-BIAS-004`. Confirm RED.
- [ ] T002 Implement `models.py` — `FeatureSnapshot`, `Label`, `Row`, frozen, with §24.1's columns.
- [ ] T003 Implement `join.py` (FR-001 to FR-005), with a named refusal per reason and a counted report.

## Phase 2: Labels (US2)

- [ ] T004 Write failing `test_labels.py`: a turning-point label's availability is the extremum's `known_at`, never `extremum_time`; max/min/no-turn within `(t, t+H]`; an unfinished horizon drops the row; a label cannot be used as a feature (SC-003, SC-004). Markers for `REQ-WP-017` and `REQ-BIAS-003`. Confirm RED.
- [ ] T005 Implement `labels.py` (FR-006 to FR-009).

## Phase 3: Folds (US3)

- [ ] T006 Write failing `test_folds.py`: folds are chronological; training rows whose horizon overlaps validation are purged; the embargo excludes rows after a validation window; shuffling is refused; the locked test split raises until unlocked; a fold left with no training rows is dropped and reported (SC-005 to SC-007). Markers for `REQ-WP-017`, `REQ-BIAS-001`, `REQ-BIAS-010`. Confirm RED.
- [ ] T007 Implement `folds.py` (FR-010 to FR-013).

## Phase 4: Universe (US4)

- [ ] T008 Write failing `test_universe.py`: a symbol listed after `t` is absent; one delisted before `t` is absent; eligibility uses trailing data only; a non-point-in-time universe is refused (SC-008). Markers for `REQ-WP-017`, `REQ-BIAS-007`, `REQ-BIAS-008`. Confirm RED.
- [ ] T009 Implement the universe in `join.py` (FR-014, FR-015).

## Phase 5: Leakage checks (US5)

- [ ] T010 Write failing `test_leakage.py`: one test per check, each constructing a dataset that violates it; a clean dataset passes and reports what was verified; an empty dataset fails (SC-009, SC-010, ADR-025). Confirm RED.
- [ ] T011 Implement `leakage.py` (FR-016, FR-017).

## Phase 6: Close

- [ ] T012 Mutation-check six guards: let the join take a later snapshot; forward-fill a missing one; label from `extremum_time` instead of `known_at`; drop the purge; let the locked split be read; make the empty-dataset check pass. Each must fail a named test. Verify every restore.
- [ ] T013 Confirm `# @trace:` markers for REQ-WP-017 and each REQ-BIAS-* on the module or test that satisfies it.
- [ ] T014 Set the six `REQ-BIAS-*` notes to `implemented` and `REQ-WP-017` to `implemented`; leave the other five BIAS notes at `draft` (ADR-024).
- [ ] T015 `make lint`, `make typecheck`, `make test`, `make validate` green.

## Coverage

| | Task |
| --- | --- |
| FR-001 to FR-005 | T003 |
| FR-006 to FR-009 | T005 |
| FR-010 to FR-013 | T007 |
| FR-014, FR-015 | T009 |
| FR-016, FR-017 | T011 |
| SC-001, SC-002 | T001 |
| SC-003, SC-004 | T004 |
| SC-005 to SC-007 | T006 |
| SC-008 | T008 |
| SC-009, SC-010 | T010 |

## Notes

The six `REQ-BIAS-*` notes are `hard_gated`, so they cannot hold `planned`:
R5 forbids any status past `specified` without a linked test. They stay at
`specified` until their tests exist and then go straight to `implemented`,
which is what `/sdd-plan`'s step 4 prescribes and what REQ-WP-019 learned the
hard way.

T012's third mutation is the one to watch. Labelling from `extremum_time`
rather than `known_at` produces a dataset that trains beautifully — the label
is available before the market could have known it — and every metric computed
on it looks like an edge.
