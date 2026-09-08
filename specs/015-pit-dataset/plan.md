# Implementation Plan: Point-in-time dataset

**Branch**: `wp-017-pit-dataset` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Five modules under `src/channelflow/dataset/`: the snapshot and row models, the
as-of join, the labeller, the fold builder, and the leakage checker. Nothing
here trains anything; it produces the rows a model would be trained on, and the
checks that say whether they are honest.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `Bar` (REQ-WP-005), `ConfirmedExtremum`
(REQ-WP-019). Nothing new.

**Storage**: none. PRD §24.1's table is unbuilt; the row shape matches its
columns so persistence later changes the source, not the meaning.

**Testing**: pytest, pure. Every leakage check has a test that constructs the
violation and asserts it is caught — a check nobody has seen fail is a check
nobody knows works.

**Target Platform**: `src/channelflow/dataset/`.

**Performance Goals**: none stated. The join is a linear scan per row; PRD
§0.14 puts correctness first, and an index is the optimisation to make when a
profile asks.

**Constraints**: FR-001 to FR-005 (the join leaks nothing), FR-010 to FR-013
(folds), FR-016 (an empty dataset fails its check — ADR-025).

**Scale/Scope**: 5 modules, ~50 tests.

## Constitution Check

- **I (no look-ahead)** — the feature. FR-002 enforces PRD §24.1's invariant at
  the point of joining, so a snapshot that saw the future cannot enter a row.
- **II (time is not one thing)** — a row carries four distinct times: the
  as-of, the snapshot's `source_max_event_time`, the label's horizon end, and
  the label's availability. Conflating the last two is PRD §41 rule 3.
- **IV (baselines before models)** — this feature exists so that the ML layer
  Principle IV gates has honest input when it is allowed to start.
- **XI (results are reproducible)** — folds are deterministic and shuffling is
  refused, so two builds of one configuration give one dataset.
- **XIV** — traces to REQ-WP-017 and six REQ-BIAS-* constraints.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/dataset/
├── __init__.py
├── models.py     # FeatureSnapshot, Label, Row: PRD §24.1's columns
├── join.py       # the as-of join, and every refusal in it
├── labels.py     # §23.5A's Target E from REQ-WP-019's confirmed extrema
├── folds.py      # §24.3's chronological folds, purge, embargo, locked test
└── leakage.py    # the checks, and what they examined

tests/unit/dataset/
├── test_join.py       # US1: SC-001, SC-002
├── test_labels.py     # US2: SC-003, SC-004
├── test_folds.py      # US3: SC-005 to SC-007
├── test_universe.py   # US4: SC-008
└── test_leakage.py    # US5: SC-009, SC-010
```

**Structure Decision**: `leakage.py` is separate from the modules it checks. A
checker living inside the thing it checks tends to be written to pass — it sees
the same intermediate state, and the temptation is to assert on that rather
than on the output. It takes a built dataset and knows nothing else.

The universe lives in `join.py` rather than its own module: it is a filter on
which rows may be built, and PRD §42 is four bullet points.

## Approach

**Every refusal is a named exception, not a `None`.** The join has five ways to
decline a row, and a caller that gets `None` five times cannot tell a missing
snapshot from a leaking one. The build's report counts each separately.

**The leakage checker reports what it examined, not only what it found.**
ADR-025: "clean" means something was checked. A rule that silently applied to
no rows is visible in the report rather than indistinguishable from a rule that
passed.

**Folds are built from label horizons, not from row counts.** The purge exists
because a label at `t` describes what happened until `t + H`; a fold boundary
drawn without `H` in hand cannot know which training rows reach across it.

**The locked test split is a method that raises.** Not a flag someone reads and
ignores — asking for it during tuning is an error with PRD §41 rule 10 in the
message.

## Complexity Tracking

> No violations.
