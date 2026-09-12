---
traces: [REQ-INFRA-004]
status: draft
---

# Feature Specification: The mutation sweep is a committed tool

**Feature Branch**: `infra-004-mutation-harness`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-INFRA-004.

## Context

Thirty-six outcome notes and five ADRs cite a mutation sweep, and phrases like
"23 of 23 caught" are the evidence on which requirements moved to `implemented`.
All of it ran from throwaway scripts, retyped per requirement and never
committed — so a flaw in one was a flaw in all of them, nobody but the author
could check a number, and the survivors' reasons lived only as prose that
nothing tested.

Three flaws demonstrate the cost. Python's bytecode cache validates on
`(mtime, size)`, so same-size mutants in succession report each other's results.
No script checked the suite was green first, so a red suite would have scored a
perfect sheet. And a mutation that breaks the module scores as caught while
telling nobody anything — which is how a corrupted specification hides.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A number anyone can reproduce (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the committed specifications, **When** the sweep is run, **Then** it reports the figures recorded in the vault.
2. **Given** a specification, **When** it is loaded, **Then** every pattern matches its source exactly once.

---

### User Story 2 - A sweep that cannot lie (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a suite that fails unmutated, **When** a sweep starts, **Then** it refuses.
2. **Given** two mutants of identical size in succession, **When** each is run, **Then** each is judged on its own code.
3. **Given** a mutation producing unparseable code, **When** it is applied, **Then** it is an error rather than a catch.
4. **Given** a pattern that no longer matches, or matches twice, **When** applied, **Then** it is an error.

---

### User Story 3 - A reason with a date on it (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a survivor with no recorded reason, **When** the sweep ends, **Then** it fails.
2. **Given** a recorded survivor that is now caught, **When** the sweep ends, **Then** it fails.
3. **Given** a recorded survivor that still survives, **When** the sweep ends, **Then** it passes.

### Edge Cases

- **A mutant that hangs.** Counted as caught; a suite would never let it through.
- **A run interrupted by a timeout.** The source is restored anyway.
- **A specification whose source file is gone.** An error on the fast gate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The sweep MUST refuse to start unless the unmutated suite passes.
- **FR-002**: Bytecode caching MUST be disabled for every run.
- **FR-003**: A pattern MUST match exactly once, or be an error.
- **FR-004**: A mutation MUST produce parseable code, or be an error.
- **FR-005**: A collection error MUST be reported as a broken mutation, not a catch.
- **FR-006**: A hang MUST count as caught.
- **FR-007**: The source MUST be restored whatever happens.
- **FR-008**: An unexplained survivor MUST fail; a recorded survivor that is caught MUST fail.
- **FR-009**: Every committed specification MUST be checked against its source on every commit.

### Key Entities

- **Specification**: a source file, a test path, and a list of mutations.
- **Mutation**: a name, a pattern, a replacement, and optionally why it survives.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The sweep reproduces the per-module figures recorded in the vault.
- **SC-002**: A red baseline is refused.
- **SC-003**: The same-size-mutant regression is covered by a test that would fail without the fix.
- **SC-004**: Every committed survivor carries a reason of substance.
- **SC-005**: The full sweep's duration is measured and recorded.

## Assumptions

- **Mutations are written by hand.** An engine would enumerate far more and mean
  far less; choosing mutations that match mistakes a person would make is the
  part that needs judgement.
- **It runs in CI while it is cheap.** [[ADR-065]] records the measurement and
  the trigger for revisiting.

## Open Questions

- **Specifications for the modules that predate this.** Thirty-six notes cite a
  sweep; six specifications exist. The rest stay unreproducible until written.
