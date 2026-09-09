---
traces: [REQ-EXP-015]
status: draft
---

# Feature Specification: Derivatives/DeFi confluence at turning points

**Feature Branch**: `exp-015-defi-confluence`

**Created**: 2026-09-09

**Input**: REQ-EXP-015 — five families, strict ablation, same walk-forward folds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ablate all five families strictly (Priority: P1)

OI/funding/liquidations; DEX-CEX executable basis; DEX depth asymmetry; swap
imbalance; LP liquidity migration.

**Why this priority**: "strict" is the requirement's own word, and an ablation
whose arms differ in two things reports the sum of two contributions under one
family's name. Nothing about that number looks wrong.

**Acceptance Scenarios**:

1. **Given** the five families, **When** the arms are built, **Then** every arm is one family from either the baseline or the full set.
2. **Given** an arm two families from both, **When** the ablation runs, **Then** it is refused by name rather than scored.
3. **Given** the DEX basis family, **When** its features are resolved, **Then** the CEX perp-spot basis is not among them.

---

### User Story 2 - Score every arm on the same walk-forward folds (Priority: P1)

One certified dataset, used as given.

**Why this priority**: the failure it guards against is a per-family study run
separately and the numbers put in one table. A difference between arms scored on
different splits is the difference between the splits as much as between the
arms.

**Acceptance Scenarios**:

1. **Given** a report, **When** its fold fingerprint is read, **Then** it is the dataset's own.
2. **Given** two reports on different folds, **When** they are compared, **Then** the comparison is refused.
3. **Given** two fold sets of the same size over different rows, **When** their fingerprints are compared, **Then** they differ.

---

### User Story 3 - Read each family in both directions (Priority: P1)

Added to the baseline alone, and removed from the full set.

**Why this priority**: the two disagree whenever families overlap, and which one
gets reported decides the conclusion. A family that helps alone and adds nothing
to the full set is carrying information something else already carries.

**Acceptance Scenarios**:

1. **Given** a family that duplicates another, **When** it is read, **Then** it helps alone and adds nothing in context, and the report lists it as redundant.
2. **Given** a family nothing else carries, **When** it is read, **Then** it helps both ways.
3. **Given** a family unrelated to the target, **When** it is read, **Then** it helps neither way.
4. **Given** a family with no features, **When** it is read, **Then** it is unmeasured rather than worthless.

---

### Edge Cases

- What happens when an arm cannot be scored? Its increment is absent rather than zero: "this family added nothing" and "there was nothing to add it to" are different findings.
- What happens when the report names an asset the dataset does not contain? Refused — a report naming an asset it never scored is a claim about that asset.
- What happens when the improvement floor is zero? Refused: every difference becomes an improvement, including the ones that are rounding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All five candidate families MUST be ablated, in the PRD's order.
- **FR-002**: Every arm MUST be one family from the baseline or from the full set, and a set of arms that is not MUST be refused.
- **FR-003**: The DEX-CEX basis family MUST NOT match the registry's CEX perp-spot basis.
- **FR-004**: Every arm MUST be scored on one fold set, and the report MUST carry that fold set's fingerprint.
- **FR-005**: A fingerprint MUST distinguish fold sets of the same size over different rows.
- **FR-006**: Comparing reports across different fold sets MUST be refused.
- **FR-007**: Each family MUST be measured added-alone and removed-from-the-full-set.
- **FR-008**: Both directions MUST share a sign convention.
- **FR-009**: An increment over an arm that did not run MUST be absent, not zero.
- **FR-010**: A family that cannot be measured MUST read as unmeasured, not as adding nothing.
- **FR-011**: The instruments MUST be a required argument and MUST be present in the data.
- **FR-012**: The improvement floor MUST be a required, positive argument, and MUST decide the readings.
- **FR-013**: The report MUST be deterministic.

### Key Entities

- **Family value**: one candidate's two increments and the reading they produce.
- **Fold fingerprint**: enough of a fold set for a reader to check that two reports shared it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Five families, one entry each; twelve arms.
- **SC-002**: The strict arm set has no violations; an arm two families away is named and refused.
- **SC-003**: `basis_bps` appears in neither the DEX basis family nor the OI family.
- **SC-004**: The report's fingerprint equals the dataset's, and the arm count of folds matches.
- **SC-005**: Two fold sets of equal size over different rows have different fingerprints, and comparing their reports raises.
- **SC-006**: A duplicated family reads as redundant and appears in the report's list.
- **SC-007**: A unique family reads as adding value both ways.
- **SC-008**: An unrelated family reads as adding nothing either way.
- **SC-009**: A family with no features reads as unmeasured.
- **SC-010**: An empty instrument list raises; naming an absent asset raises.
- **SC-011**: An omitted improvement floor raises; a floor of zero raises.
- **SC-012**: The same family reads as adding value at one floor and as adding nothing at a higher one.
- **SC-013**: Two runs produce equal reports.

## Assumptions

- **The baseline is the channel state alone**, which is what every other ablation in this repository measures against.
- **Feature families are resolved by name prefix from the registry**, so an arm cannot claim a feature that does not exist.
- **Scoring is [[REQ-WP-019]]'s direct baseline**, unchanged. A second scoring path would make these numbers incomparable with every other experiment's.
