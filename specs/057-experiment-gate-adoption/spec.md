---
traces: [REQ-BIAS-011]
status: draft
---

# Feature Specification: The experiments adopt the reporting gate

**Feature Branch**: `bias-011-experiment-adoption`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-BIAS-011 — "Store all discarded experiment variants to reduce silent cherry-picking" (PRD §41 rule 11). [[REQ-REPRO-001]] built the mechanism; [[ADR-054]] records that nothing reports through it.

## Context

[[REQ-REPRO-001]] built a registry on the canonical plane and a gate, `publish`,
that refuses a winner whose field is not on record. [[ADR-054]] then recorded the
honest limit of what that achieved:

> Rule 11 is enforceable and not yet enforced. The mechanism exists; none of the
> seventeen research modules reports through it.

This specification is the other half. It does not change the gate. It makes the
eighteen research entry points able to pass through it, and makes "all of them
do" a fact the suite checks rather than a claim this document makes.

The distinction that shapes everything below: **a registry that is merely
available is an honour system with a database attached.** Adoption is not
"eighteen modules gain a call to `record`". It is the field becoming something
each comparison can be *asked* for, so that a comparison which cannot answer is
a failing test.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A comparison names the field it compared (Priority: P1)

A researcher runs one of the eighteen experiments. The result they get back can
be asked which variants it compared and what distinguished each one, without
knowing which experiment it came from.

**Why this priority**: Nothing else is possible until the field is a property of
the result. The gate takes a field; today each result holds one in a shape only
its own module understands.

**Independent Test**: Ask every comparison type in the research package for its
field and its per-variant configs; each answers.

**Acceptance Scenarios**:

1. **Given** a comparison over N variants, **When** it is asked for its field, **Then** it names all N, including the ones that failed or were discarded.
2. **Given** two variants that differed in configuration, **When** each is asked for its config, **Then** the two configs differ.
3. **Given** a comparison that deliberately names no winner, **When** it is asked which variant was chosen, **Then** it answers "none" rather than inventing one.

---

### User Story 2 - Reporting a result puts the whole field on record (Priority: P1)

A researcher reports a result. Every variant it was chosen from is recorded —
kept and discarded alike — and a result that names a winner goes through the
gate, which refuses it if any variant is missing.

**Why this priority**: This is rule 11 itself. Recording without the gate is the
honour system; the gate without recording refuses everything.

**Independent Test**: Report a comparison through the seam and read the registry
back: every variant is there, each with its own identity.

**Acceptance Scenarios**:

1. **Given** a comparison over N variants, **When** it is reported, **Then** the registry holds N runs, one per variant.
2. **Given** a comparison that names a winner, **When** it is reported, **Then** the result passes through the gate and is refused if the run is not reproducible.
3. **Given** a comparison that names no winner, **When** it is reported, **Then** the field is recorded and no winner is claimed.
4. **Given** a field already on record, **When** the same comparison is reported again, **Then** nothing is written twice.

---

### User Story 3 - A new experiment cannot quietly skip the gate (Priority: P1)

Someone adds an eighteenth experiment. If its result cannot name its field, the
suite fails and says so, naming the module.

**Why this priority**: Without it this specification decays the moment it is
satisfied. Eighteen modules adopting today is a snapshot; the next module is
what decides whether rule 11 is enforced or was enforced once.

**Independent Test**: Add a module to the research package whose comparison does
not name a field; the suite goes red naming that module.

**Acceptance Scenarios**:

1. **Given** the research package, **When** the suite runs, **Then** every module in it is checked, with no hand-maintained list of which ones to check.
2. **Given** a module whose comparison does not name its field, **When** the suite runs, **Then** it fails naming that module.

### Edge Cases

- **A variant that failed to run.** It is still a variant that was tried, and it is recorded. A field that quietly omits its failures is the shape of cherry-picking rule 11 is about.
- **A field of one.** Legitimate — a study with nothing to compare against is not a choice — and recorded as such. Already accepted by the gate.
- **A comparison run twice over the same input.** The registry is append-only ([[ADR-056]]); reporting the same field twice must not double it.
- **A variant whose config cannot be hashed.** Refused loudly rather than recorded under a config of `""`, which would say the run had no configuration.
- **Two variants with the same name.** Already refused by the gate; the field must not be able to produce it in the first place.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every comparison produced by the research package MUST be able to name the variants it compared.
- **FR-002**: A field MUST include variants that failed, were discarded, or scored worst — every variant that was tried.
- **FR-003**: A comparison MUST give a per-variant configuration that differs whenever the variants differed.
- **FR-004**: A comparison MUST say which variant it chose, or that it chose none; it MUST NOT be forced to name one.
- **FR-005**: A field MUST NOT contain the same variant name twice.
- **FR-006**: Reporting a comparison MUST record every variant in the registry, whatever its outcome.
- **FR-007**: A recorded variant MUST carry the outcome that distinguishes the chosen one from the rest.
- **FR-008**: A comparison that names a winner MUST be reported through the existing gate, unchanged.
- **FR-009**: A comparison that names no winner MUST record its field without claiming a winner.
- **FR-010**: Reporting the same field twice MUST NOT write it twice.
- **FR-011**: A variant configuration that cannot be hashed MUST be refused rather than recorded as absent.
- **FR-012**: The suite MUST check every module in the research package, discovered rather than listed.
- **FR-013**: A research module whose comparison cannot name its field MUST fail the suite, naming the module.
- **FR-014**: Nothing in this feature MUST change what any existing experiment computes or reports as its metrics.

### Key Entities

- **Field**: what a comparison compared — a variant name to the configuration that distinguishes it, plus the variant it chose, if any.
- **Seam**: the one place a comparison becomes registry rows and, when there is a winner, a report through the gate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every comparison type in the research package answers when asked for its field; the count of those that do equals the count of modules.
- **SC-002**: For every comparison, the number of variants in its field equals the number the experiment ran, failures included.
- **SC-003**: Two variants that differed in configuration hash differently; two identical ones hash the same.
- **SC-004**: Reporting a comparison of N variants leaves N runs in the registry.
- **SC-005**: A winner reported with one variant missing from the registry is refused, naming the missing variant.
- **SC-006**: A comparison naming no winner records N runs and produces no report.
- **SC-007**: Reporting one field twice leaves N runs, not 2N.
- **SC-008**: Adding a research module that cannot name its field turns the suite red, and the failure names the module.
- **SC-009**: Every existing experiment's metrics are byte-identical before and after this change.

## Assumptions

- **The gate does not change.** `publish` and the registry are [[REQ-REPRO-001]]'s and are used as they are. If this work needs the gate to change, that is a finding about the gate, recorded rather than absorbed.
- **The dataset, code version and model artifact come from the caller**, not from the research functions. A research function is pure over bars; it has no store, no git, and no clock, and giving it any of the three would break [[REQ-REPRO-001]]'s FR-013.
- **A variant's configuration is whatever distinguishes it within its field.** Where a comparison currently discards that — keeping a variant's name and not its parameters — it starts keeping it. A config hash that cannot tell two different configurations apart is a broken hash, not a cheaper one.
- **Adoption is all eighteen or none.** A subset would claim the coverage [[ADR-024]] refused to claim for rule 2 on the strength of one engine's guard, and [[ADR-054]] refused for this rule already.
- **`ablation` is one of the eighteen** although its requirement is `REQ-US-006`/`-007` rather than an `REQ-EXP-*`. It compares arms and picks a ranking, which is the behaviour rule 11 is about; its requirement id is not.
