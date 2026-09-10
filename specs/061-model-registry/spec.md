---
traces: [REQ-WP-022]
status: draft
---

# Feature Specification: A fitted model is registered, hashed and citable

**Feature Branch**: `wp-022-model-registry`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-022 — PRD §23.9's eleven fields, and PRD §0 item 13's fourth hash.

## Context

PRD §0 item 13 requires every research result to be reproducible from a
versioned dataset, a config, a code commit and a model artifact hash.
[[REQ-REPRO-001]] built all four components and three of them have producers.
The fourth does not: `ModelArtifact` appears nowhere outside
`channelflow.experiments`, so every run that fitted a model records
`UNRECORDED` — the value whose entire job is to say the run cannot be repeated.

Models today are constructed by a caller, fitted in place, and dropped. Two runs
of one experiment over one dataset leave two models nothing can tell apart, and a
result quoting one cites something that no longer exists.

PRD §23.9 names eleven fields the registration carries. One of them is the
artifact hash, which means the hash identifies **the model**, not the
registration describing it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A fitted model has an identity (Priority: P1)

A model that has been fitted can be asked for a hash of what it learned.

**Why this priority**: Everything else is bookkeeping around this. Without it
the fourth hash has no content.

**Acceptance Scenarios**:

1. **Given** two models fitted on identical data with identical settings, **When** each is hashed, **Then** the hashes are equal.
2. **Given** two models differing in a fitted parameter, **When** each is hashed, **Then** the hashes differ.
3. **Given** two models differing only in a hyperparameter but fitting to the same parameters, **When** each is hashed, **Then** the hashes differ — a model is what it learned *and* how it was told to learn.
4. **Given** a model that has not been fitted, **When** it is asked for a hash, **Then** it is refused rather than hashed.

---

### User Story 2 - The registration carries what §23.9 asks for (Priority: P1)

Eleven fields, none defaulted silently.

**Acceptance Scenarios**:

1. **Given** a registration, **When** it is built, **Then** it carries model type, feature set versions, train and validation spans, code commit, hyperparameters, scaler parameters, calibration model, metrics, artifact hash and deployment status.
2. **Given** a registration missing any of them, **When** it is built, **Then** it is refused naming the field.
3. **Given** a train span that overlaps its validation span, **When** it is built, **Then** it is refused — a model validated on rows it was trained on is not validated.

---

### User Story 3 - A run can cite a model that exists (Priority: P1)

An experiment run records a registered artifact hash instead of `UNRECORDED`,
and one citing an unregistered hash is refused.

**Why this priority**: This is the point. A hash nobody can resolve is a
different kind of unreproducible from no hash at all, and the gate should not
accept either.

**Acceptance Scenarios**:

1. **Given** a registered model, **When** a run cites its hash, **Then** the run is reproducible and reportable.
2. **Given** a hash no registration carries, **When** a run cites it, **Then** it is refused naming the hash.
3. **Given** a registration stored twice, **When** the registry is read, **Then** it appears once.

### Edge Cases

- **A model fitted twice on the same data.** Same hash — that is what makes it citable.
- **Floating-point state.** Two fits differing in the last bit are different models and hash differently; a hash that rounded them together would lie about the one thing it exists to certify.
- **A registration read back from storage.** Every field equals what was written, and the artifact hash is not recomputed on read — a hash recomputed from a description is a hash of the description.
- **An empty metrics mapping.** Refused: a model registered with no measurement was not evaluated, and PRD §45's Phase 7 acceptance turns on measurements.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A fitted model MUST produce a hash derived from its own parameters and its hyperparameters.
- **FR-002**: Two models fitted identically MUST hash identically; any difference MUST change the hash.
- **FR-003**: A model MUST say whether it has been fitted, and an unfitted one MUST be refused rather than hashed.
- **FR-004**: The hash MUST be framed so no component can borrow a character from the next.
- **FR-005**: A registration MUST carry all eleven of PRD §23.9's fields.
- **FR-006**: A missing or empty field MUST be refused, naming it.
- **FR-007**: A train span overlapping its validation span MUST be refused.
- **FR-008**: Registrations MUST be stored on the canonical plane and read back identically, with the artifact hash read rather than recomputed.
- **FR-009**: Storing one registration twice MUST NOT produce two.
- **FR-010**: A run citing a registered hash MUST be reproducible; one citing an unregistered hash MUST be refused, naming it.
- **FR-011**: Nothing existing MUST change what it computes.

### Key Entities

- **Artifact hash**: what a fitted model is, as a value.
- **Registration**: PRD §23.9's eleven fields about one artifact.
- **Model registry**: registrations on the canonical plane.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two identical fits hash equal; a one-parameter difference hashes different.
- **SC-002**: An unfitted model raises rather than returning a hash.
- **SC-003**: A registration missing any of the eleven fields raises naming it.
- **SC-004**: Overlapping train and validation spans raise.
- **SC-005**: Every field read back equals what was written, artifact hash included.
- **SC-006**: Storing one registration twice leaves one.
- **SC-007**: A run citing a registered hash publishes; one citing an unknown hash is refused naming the hash.
- **SC-008**: Every existing test passes unchanged.

## Assumptions

- **The hash is over exact bytes.** Two fits differing in the last bit produce different probabilities, so they are different models. A platform that produces different bytes produces a different artifact, and that is honest rather than inconvenient.
- **The model protocol gains one member.** Each model says whether it is fitted, because only it knows. This mirrors `Transform.centered`, which has no default so an author cannot skip the question.
- **Deployment status is stored, not acted on.** Deciding promotion belongs to [[REQ-EXP-008]] and the gate.
- **The API does not serve the registry.** Its consumer is the experiment registry, which cites an artifact hash the moment one exists — a real consumer here, not a promised one.
