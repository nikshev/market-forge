---
traces: [REQ-NRT-REPAINT, REQ-NRT-LEAK]
status: draft
---

# Feature Specification: Repaint and future-leak suites that enumerate

**Feature Branch**: `wp-nrt-repaint-leak`

**Created**: 2026-09-15

**Status**: Draft

**Input**: [[REQ-NRT-REPAINT]] (PRD §35.3) and [[REQ-NRT-LEAK]] (PRD §35.4).
One spec because §35.4 ends "This should be an automated CI suite" and both
requirements are the same shape.

## Context

Both properties hold today in spot checks. Neither is enumerated, so both grow a
hole every time something is added.

**§35.3.** `test_appending_future_bars_does_not_change_a_past_snapshot` fits one
model at one moment, appends future bars, **refits that moment** and compares.
That proves the fit is a function of its prefix — real, and what it was written
for. §35.3 asks for something else: *store* the snapshots and assert the
**stored** ones are unchanged. A refit builds a fresh answer each time and never
looks at the old one, so it cannot see a model that returns a correct value and
then mutates what it already handed out — a snapshot holding a view into a
rolling buffer, a cached array reused between calls, a field filled in later.

Four models exist. `KalmanChannel` is where this matters most: a filter carries
state between bars by design.

**§35.4.** The feature registry holds **27** specifications exposing **55**
names. `tests/unit/dataset/test_leakage.py` checks assembled *rows* — that a
feature's availability is not after `t`. §35.4 checks the *computation*: run it
over a truncated input and over a full one, and demand the same answer. A feature
whose implementation peeks at a later row produces rows that pass the first check
and values that fail this one.

Both requirements are `hard_gated`, so rule R5 — the one this project never
waives — forbids either advancing past `specified` without a linked test.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A stored snapshot is still what it was (Priority: P1)

**Acceptance**: bars are fed one at a time; after each, a snapshot is taken and
kept. After every later bar, every kept snapshot equals what it was when kept.
The object compared is the object handed out, not a fresh fit of the same moment.

### User Story 2 - Every channel model is checked (Priority: P1)

**Acceptance**: the models are enumerated from the package. A model added later
without this check is a red suite, naming the model.

### User Story 3 - A repainting model is caught and named (Priority: P1)

**Acceptance**: a model written to mutate a snapshot it already returned makes
the suite fail, and the failure names the model, the snapshot's moment and the
field that changed.

### User Story 4 - Every feature is computed twice (Priority: P1)

**Acceptance**: for each registered feature, the value at `t` from input
truncated at `t` equals the value at `t` from the full input.

### User Story 5 - A feature with no case is a failure, not a gap (Priority: P1)

**Acceptance**: a registered feature with no truncation case fails the suite and
names the feature. A feature that genuinely cannot be checked this way is
**refused with a recorded reason** rather than skipped — a skip reports green.

### User Story 6 - A leaking feature is caught and named (Priority: P1)

**Acceptance**: a feature written to read a later row makes the suite fail, and
the failure names the feature and both values.

### Edge Cases

- Comparing only a chosen field passes a model that repaints a different one. The
  comparison covers the whole snapshot.
- A snapshot compared against a copy taken at storage time proves nothing if the
  copy is shallow and the mutation is inside a nested value.
- A model that returns the *same object* every call trivially satisfies "all
  snapshots equal" if equality is identity. Equality must be by value.
- A feature whose value legitimately differs — one that is a function of the
  whole dataset by definition — is a refusal with a reason, never a skip.
- A tolerance chosen after seeing the failures is not a tolerance; it is the
  failure, renamed.
- An enumeration that finds nothing reports success. Each suite asserts how many
  models and features it examined.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Snapshots are retained as produced and compared later against a
  deep copy taken at production time.
- **FR-002**: Equality is by value over the entire snapshot, and identity does
  not satisfy it.
- **FR-003**: Channel models are enumerated from the package; the count is
  asserted.
- **FR-004**: Every registered feature specification participates; the count is
  asserted.
- **FR-005**: A registered feature with no truncation case fails, naming it.
- **FR-006**: A feature that cannot be checked is refused with a recorded reason
  that the enumeration reads; skipping is not available.
- **FR-007**: Numeric comparison uses a stated tolerance, exact for integers,
  documented where it is defined.
- **FR-008**: A deliberately repainting model and a deliberately leaking feature
  each make their suite fail, with a message naming what and where.
- **FR-009**: Both suites run with no services and no network.

### Key Entities

- **Retained snapshot**: the moment it describes, the value as produced, and a
  deep copy taken at that instant.
- **Truncation case**: a feature, an input, a `t`, and the value expected from
  both the truncated and the full run.
- **Refusal**: a feature that cannot be checked, and the reason — carried, not
  silent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four channel models are exercised, and the suite fails if a
  fifth appears without one.
- **SC-002**: All 27 registered feature specifications are covered, and the suite
  fails if a 28th appears without a case.
- **SC-003**: A repainting model and a leaking feature are each caught by a test
  that introduces the fault on purpose.
- **SC-004**: Neither suite can report success having examined nothing — each
  asserts its own coverage count.
- **SC-005**: Both suites run in the fast gate, needing no services and no
  network.

## Assumptions

- **A feature's truncation case supplies its own input.** The registry describes
  a feature; it does not carry sample data. Each case names the input it uses, so
  a feature's check is readable beside the feature.
- **The tolerance is relative, not absolute**, and stated once rather than per
  feature. Absolute tolerance is meaningless across features whose units range
  from a ratio to a notional.
- **"Every feature" means every registered specification**, not every exposed
  name. A specification exposing several columns is checked across all of them,
  because a leak in one column is a leak.
- **Refusals are expected to be rare and are reviewed.** The mechanism exists so
  that an unverifiable feature is visible, not so that it is convenient.
