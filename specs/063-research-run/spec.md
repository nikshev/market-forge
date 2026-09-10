---
traces: [REQ-WP-024]
status: draft
---

# Feature Specification: One research run, end to end

**Feature Branch**: `wp-024-research-run`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-024 — the caller five requirements each assumed.

## Context

Five mechanisms exist and nothing calls any of them. A `RunIdentity` is never
assembled; the field seam is never reached from production code; no path fits a
model and registers its artifact; calibration per horizon has no caller.

Each of those was recorded honestly as an open question, and each answered it
with "a caller will do it". This specification is that caller, for one
experiment.

The reason it is worth doing as a unit rather than five wires: **every one of
those mechanisms refuses something.** A dirty working tree, an artifact nobody
registered, a variant missing from its own field, a horizon too thin to speak.
Separately each refusal is theoretical. Assembled, they decide whether a result
may be reported at all, and a run that fails says which component stopped it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A run's models are registered as it runs (Priority: P1)

The models a comparison fits are hashed and registered without being fitted
twice.

**Why this priority**: Refitting to obtain a hash would be a second scoring
path, and this repository has refused that consistently — a comparison is only
honest if one code path produced both numbers.

**Acceptance Scenarios**:

1. **Given** a comparison, **When** it runs, **Then** each model it fitted reports its artifact hash alongside its score.
2. **Given** a run over several folds, **When** a variant's artifact is cited, **Then** it covers all of that variant's folds together rather than one of them.
3. **Given** an existing caller of the comparison, **When** it runs, **Then** what it reads is unchanged.

---

### User Story 2 - The four hashes are assembled and checked together (Priority: P1)

A run produces an identity per variant, and the gate accepts or refuses it.

**Acceptance Scenarios**:

1. **Given** a clean tree, a dataset reference, registered artifacts and hashed configs, **When** a run reports, **Then** it publishes and every variant is on record.
2. **Given** a dirty working tree, **When** a run reports, **Then** it is refused, naming the code component.
3. **Given** a variant whose artifact was not registered, **When** a run reports, **Then** it is refused, naming the artifact.
4. **Given** two runs over one dataset with one code version, **When** their identities are compared, **Then** the run hashes are equal.

---

### User Story 3 - Reliability is reported at each horizon (Priority: P2)

The result carries calibration per horizon for the rows the run scored.

**Acceptance Scenarios**:

1. **Given** validation rows spanning two horizons, **When** a run reports, **Then** there is a slice for each.
2. **Given** a horizon with too few rows, **When** a run reports, **Then** it is unmeasured rather than curved.

### Edge Cases

- **A fold that could not be scored.** It is already dropped with a reason; a variant with no scored fold has no artifact and must not be published as if it had one.
- **A variant that failed entirely.** Still on record — PRD §41 rule 11 is about the ones that did not survive.
- **A dataset whose folds are all unscorable.** Refused rather than reported as a run with an empty field.
- **A run reported twice.** The registries hold one copy of each, as their own requirements already guarantee.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A comparison MUST report the artifact hash of each model it fitted, without fitting anything twice.
- **FR-002**: A variant's run-level artifact MUST cover all of its scored folds together.
- **FR-003**: Existing readers of the comparison MUST see no change in what they already read.
- **FR-004**: A run MUST register each variant's artifact before citing it.
- **FR-005**: A run MUST assemble a `RunIdentity` per variant from all four components.
- **FR-006**: Every variant MUST be on record before any winner is published.
- **FR-007**: A run over a dirty tree MUST be refused, naming the component.
- **FR-008**: A run citing an unregistered artifact MUST be refused, naming it.
- **FR-009**: Two runs over one dataset and code version MUST produce equal run hashes.
- **FR-010**: The result MUST carry calibration per horizon over the rows scored.
- **FR-011**: A variant with no scored fold MUST NOT be published as a winner.
- **FR-012**: A dataset with nothing scorable MUST be refused.

### Key Entities

- **Study result**: what one run produced — the comparison, the registrations it made, the report the gate returned, and reliability per horizon.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each scored model in a comparison carries a non-empty artifact hash; the count equals the models fitted.
- **SC-002**: A variant's run artifact changes when any of its folds changes and not otherwise.
- **SC-003**: After a run, the model registry holds one registration per scored variant.
- **SC-004**: After a run, the experiment registry holds one run per variant, whatever its outcome.
- **SC-005**: A dirty tree produces a refusal naming the code component and no published report.
- **SC-006**: An unregistered artifact produces a refusal naming it.
- **SC-007**: Two runs over one dataset and code version produce equal run hashes.
- **SC-008**: The result's horizon slices match the horizons in the scored rows.
- **SC-009**: Every existing test passes unchanged.

## Assumptions

- **The comparison reports artifacts; the run does not refit.** The alternative is a second scoring path, which this repository has refused wherever it has come up.
- **`Score.artifact` is optional**, so a caller that supplies its own predictions — as two experiments already do — reports no artifact rather than a false one.
- **The dataset reference and code version are the caller's.** A research function reads no store, no git and no clock; [[REQ-REPRO-001]]'s FR-013.
- **One experiment is wired.** A second is a second caller of the same path, and if it needs a different one that is a finding about the path.
- **`require_causal` is out of scope.** It belongs at a live feature path's entrance and a research run is not one; [[REQ-BIAS-002]]'s third gap stays where it is.
