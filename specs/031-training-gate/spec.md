---
traces: [REQ-US-007]
status: draft
---

# Feature Specification: Nothing trains on an unchecked dataset

**Feature Branch**: `us-007-leakage-gate`

**Created**: 2026-09-09

**Input**: REQ-US-007 — "the training dataset passes leakage assertions before
being used for ML/GMDH training." PRD §24.2, §24.3 and §41.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Make the check a precondition, not a habit (Priority: P1)

Training takes a dataset that has been checked, and there is no way to hand it
one that has not.

**Why this priority**: the checks already exist and already run in tests. What
REQ-US-007 asks for is a *guarantee*, and a check someone has to remember is not
one. The failure is silent: a leaked dataset trains fine and scores well.

**Acceptance Scenarios**:

1. **Given** clean rows and folds, **When** they are certified, **Then** training accepts the result.
2. **Given** rows with a leak, **When** they are certified, **Then** certification is refused and the findings are named.
3. **Given** folds whose training rows reach into a validation window, **When** they are certified, **Then** certification is refused.
4. **Given** an uncertified fold list, **When** it is passed to training, **Then** it is refused.
5. **Given** an empty dataset, **When** it is certified, **Then** it is refused — every "no row violates X" check passes over nothing.

---

### User Story 2 - Leave no way around it (Priority: P1)

A certificate cannot be constructed except by passing the checks.

**Why this priority**: a gate with a back door is documentation. If a
certificate can be built by hand, the first person in a hurry builds one.

**Acceptance Scenarios**:

1. **Given** an unclean report, **When** a certificate is constructed with it, **Then** construction is refused.
2. **Given** a certificate, **When** its reports are read, **Then** both the row report and the fold report are present and clean.
3. **Given** a certificate, **When** it is read, **Then** it says how many rows and folds were examined, and by which rules.
4. **Given** every training entry point, **When** their signatures are inspected, **Then** each requires a certificate rather than a fold list.

---

### Edge Cases

- What happens when the rows are clean but the folds are not? Certification is refused and both reports travel with the refusal, so the reader sees which half failed.
- What happens when a caller certifies once and then mutates the folds? The certificate holds the folds it certified, and training reads them from it — so a later mutation of the caller's own list changes nothing the model sees.
- What happens when a dataset is certified twice? Two equal certificates. The checks are pure.
- What happens to a research procedure that only reads a dataset without fitting? It is not training and needs no certificate. The gate is on fitting, which is where a leak becomes a number someone believes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A certificate MUST hold the folds it certified, the row report and the fold report.
- **FR-002**: A certificate MUST NOT be constructible with an unclean report of either kind.
- **FR-003**: Certification MUST run both `check_rows` and `check_folds`, and MUST refuse on any finding.
- **FR-004**: Certification MUST refuse an empty dataset.
- **FR-005**: A refusal MUST name the findings.
- **FR-006**: Every training entry point MUST take a certificate, and MUST refuse a bare fold list.
- **FR-007**: Training MUST read its folds from the certificate, not from the caller.
- **FR-008**: A certificate MUST report what was examined, by rule.
- **FR-009**: Certifying one dataset twice MUST produce equal certificates.

### Key Entities

- **Certificate**: certified folds, and the two reports that certified them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean dataset certifies, and training accepts the certificate.
- **SC-002**: A leaked row refuses, naming the rule.
- **SC-003**: A contaminated fold refuses.
- **SC-004**: An empty dataset refuses.
- **SC-005**: A certificate cannot be built around an unclean report.
- **SC-006**: Passing a bare fold list to any training entry point refuses.
- **SC-007**: Every training entry point requires a certificate, verified over their signatures.
- **SC-008**: Two certifications of one dataset are equal.

## Assumptions

- **The checks themselves are [[REQ-WP-017]]'s**, and are not rewritten here. This adds the precondition, not the arithmetic.
- **"Training" means fitting a model on a dataset**: the direct baseline, the derivative experiment and the ablation. A procedure that reads a dataset without fitting is not training.
- **The GMDH search takes arrays, not folds**, so the gate sits at the fold level where the dataset still exists as rows with labels and times.
