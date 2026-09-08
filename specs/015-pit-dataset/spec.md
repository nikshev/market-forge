---
traces: [REQ-WP-017, REQ-BIAS-001, REQ-BIAS-003, REQ-BIAS-004, REQ-BIAS-007, REQ-BIAS-008, REQ-BIAS-010]
status: draft
---

# Feature Specification: Point-in-time dataset

**Feature Branch**: `wp-017-pit-dataset`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-017 — as-of joins; leakage asserts; labels; purged
chronological folds. Six of PRD §41's anti-bias rules, all `hard_gated`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Join features to labels without leaking (Priority: P1)

A training row pairs the features that were available at time `t` with a label
about what happened after `t`. No feature in the row was computed from anything
later than `t`.

**Why this priority**: PRD §24.2 is the whole feature: "Labels may use future
data. Features may not." Every model built on this repository will be built on
rows this produces, and a leak here is invisible in every metric downstream —
it makes the model look better, which is the one direction nobody
investigates.

**Independent Test**: Build a dataset from feature snapshots straddling `t`,
and assert every joined value came from a snapshot at or before `t`.

**Acceptance Scenarios**:

1. **Given** feature snapshots before and after `t`, **When** a row for `t` is built, **Then** only snapshots at or before `t` are joined.
2. **Given** a snapshot whose `source_max_event_time` is after its `as_of_time`, **When** the join runs, **Then** it is refused — PRD §24.1's invariant.
3. **Given** several snapshots at or before `t`, **When** a row is built, **Then** the most recent is used.
4. **Given** no snapshot at or before `t`, **When** a row is built, **Then** the row is dropped and counted, not filled with a later value.
5. **Given** a feature derived from a bar that had not closed at `t`, **When** the join runs, **Then** it is refused.

---

### User Story 2 - Label from what was confirmable (Priority: P1)

A label says whether a turning point occurred within a horizon, and carries the
time the system could first have known it.

**Why this priority**: PRD §41 rule 3 — "No pivot that requires future bars
unless the feature availability time is shifted to confirmation time." The
turning points of REQ-WP-019 already carry `known_at`; this is what makes them
usable as targets without leaking.

**Independent Test**: Label a series from confirmed extrema and assert each
label's availability time is the extremum's `known_at`, never its
`extremum_time`.

**Acceptance Scenarios**:

1. **Given** a confirmed extremum, **When** it becomes a label, **Then** the label's availability is the extremum's `known_at`.
2. **Given** a horizon `H`, **When** a row at `t` is labelled, **Then** the label states whether a maximum, a minimum, or neither occurred in `(t, t + H]`.
3. **Given** a row whose horizon extends past the end of the data, **When** it is labelled, **Then** the row is dropped — an unfinished horizon is not a "no turn".
4. **Given** a label, **When** it is used as a feature, **Then** it is refused; labels are targets only.

---

### User Story 3 - Split time without contaminating it (Priority: P1)

Folds are chronological, with a purge and an embargo around each boundary, and
the test split cannot be read while parameters are being tuned.

**Why this priority**: PRD §24.3 and §41 rules 1 and 10. A shuffled split on
overlapping-horizon labels produces a validation score that is a memory of the
training set, and the number looks exactly like a good one.

**Independent Test**: Build folds over labelled rows with overlapping horizons
and assert no training row's horizon reaches into its validation window.

**Acceptance Scenarios**:

1. **Given** labelled rows, **When** folds are built, **Then** each fold's training rows all precede its validation rows.
2. **Given** a horizon `H`, **When** folds are built, **Then** training rows whose horizon overlaps the validation window are purged.
3. **Given** an embargo, **When** folds are built, **Then** rows within it after the validation window are excluded from the next training set.
4. **Given** a request to shuffle, **When** folds are built, **Then** it is refused.
5. **Given** a locked test split, **When** it is requested during tuning, **Then** it is refused, and the refusal names the rule.

---

### User Story 4 - Reconstruct the universe as it was (Priority: P2)

The set of symbols eligible at time `t` is what was listed and liquid then, not
what is listed and liquid now.

**Why this priority**: PRD §41 rules 7 and 8, and §42. P2 because a
single-symbol dataset is usable without it — but a multi-asset backtest without
it measures the survivors.

**Independent Test**: A universe with listings and delistings, queried at
several instants.

**Acceptance Scenarios**:

1. **Given** a symbol listed after `t`, **When** the universe at `t` is built, **Then** it is absent.
2. **Given** a symbol delisted before `t`, **When** the universe at `t` is built, **Then** it is absent.
3. **Given** an eligibility rule on trailing volume, **When** it is evaluated at `t`, **Then** it uses only volume observed at or before `t`.
4. **Given** a dataset built over a universe, **When** the universe is not point-in-time, **Then** the build is refused.

---

### User Story 5 - Be told when the dataset leaks (Priority: P1)

A built dataset is checked, and the check names what leaked.

**Why this priority**: REQ-WP-017's second acceptance criterion. Every rule
above is a property someone can accidentally break later; the assertions are
what make that a failure rather than a better-looking model.

**Independent Test**: Construct a deliberately leaking dataset and assert each
check catches it.

**Acceptance Scenarios**:

1. **Given** a row whose feature time is after its as-of time, **When** the dataset is checked, **Then** the check fails and names the row and the field.
2. **Given** folds whose train and validation overlap, **When** the dataset is checked, **Then** the check fails.
3. **Given** a clean dataset, **When** it is checked, **Then** the check passes and reports what it verified.
4. **Given** an empty dataset, **When** it is checked, **Then** the check fails — a check that passes over no rows proves nothing.

---

### Edge Cases

- What happens when two feature snapshots share an `as_of_time`? The one with the later `source_max_event_time` is used; if those match too, the build is refused, because the tie cannot be broken by anything the data records.
- What happens when a label's horizon contains no bars? The row is dropped, not labelled "no turn" — a horizon with no observations says nothing about what happened in it.
- What happens when the purge removes every training row from a fold? The fold is dropped and reported, rather than yielding a fold trained on nothing.
- What happens when the embargo is longer than the gap between folds? The build is refused: the configuration cannot produce non-overlapping folds and silently producing fewer would hide that.
- What happens when a feature snapshot arrives for a symbol not in the universe at that time? It is excluded, and the exclusion is counted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A row at `t` MUST join only feature snapshots with `as_of_time <= t`.
- **FR-002**: The join MUST refuse any snapshot with `source_max_event_time > as_of_time` (PRD §24.1).
- **FR-003**: Where several snapshots qualify, the join MUST use the most recent by `as_of_time`.
- **FR-004**: A row with no qualifying snapshot MUST be dropped and counted, never forward-filled from a later value.
- **FR-005**: The join MUST refuse a feature derived from a bar not finalized at `t`.
- **FR-006**: A label MUST carry the time the fact became knowable, and for a turning point that is the extremum's `known_at`.
- **FR-007**: A label MUST state maximum, minimum or no-turn within `(t, t + H]`.
- **FR-008**: A row whose horizon extends past the available data MUST be dropped.
- **FR-009**: Labels MUST NOT be usable as features.
- **FR-010**: Folds MUST be chronological; shuffling MUST be refused.
- **FR-011**: Training rows whose label horizon overlaps a validation window MUST be purged.
- **FR-012**: An embargo after each validation window MUST exclude rows from the following training set.
- **FR-013**: A locked test split MUST be refusable, and refused unless explicitly unlocked.
- **FR-014**: A universe at `t` MUST contain only symbols listed and not delisted at `t`, with eligibility computed from trailing data only.
- **FR-015**: Building a multi-symbol dataset over a non-point-in-time universe MUST be refused.
- **FR-016**: A leakage check MUST fail on an empty dataset.
- **FR-017**: A leakage check MUST name the row and field it failed on.

### Key Entities

- **Feature snapshot**: a value, when it was as of, and the latest event that fed it.
- **Row**: features as of `t`, a label about after `t`, and the times both became knowable.
- **Fold**: a training window, a validation window, and the gap the purge and embargo carve between them.
- **Universe**: which symbols existed and were eligible at a given instant.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For rows built from snapshots straddling `t`, every joined value comes from at or before `t`.
- **SC-002**: A snapshot violating §24.1's invariant is refused, naming it.
- **SC-003**: Turning-point labels carry `known_at`, and never `extremum_time`, as their availability.
- **SC-004**: Rows with unfinished horizons are absent from the dataset and counted in its report.
- **SC-005**: No training row in any fold has a label horizon reaching into that fold's validation window.
- **SC-006**: A shuffle request is refused.
- **SC-007**: The locked test split is unreadable until explicitly unlocked.
- **SC-008**: A universe query at `t` excludes symbols listed after or delisted before it.
- **SC-009**: Each leakage check catches a dataset constructed to violate it.
- **SC-010**: A leakage check over an empty dataset fails.

## Assumptions

- **No storage.** PRD §24.1's feature snapshot table is unbuilt; the dataset is built from values in memory, as everything else here is. The row shape matches the table's columns so that persistence later is a change of source, not of meaning.
- **Labels come from REQ-WP-019's confirmed extrema.** PRD §23.5A's Target E is the classification this supports; §23.5B's regression targets are not built.
- **No model.** Principle IV forbids one until baselines pass leakage tests, and this feature is what makes those tests possible. The dataset is the input to work that has not started.
- **PRD §41's rules 2, 5, 6, 9 and 11 are not covered.** Rule 2 is enforced for the extrema engine by REQ-NRT-D and has no general home yet; 5 needs REQ-WP-013's funding, 6 needs REQ-WP-014's DEX state, 9 is deferred by ADR-009, and 11 is experiment tracking. They stay at `draft`.
