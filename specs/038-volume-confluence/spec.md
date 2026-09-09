---
traces: [REQ-EXP-005]
status: draft
---

# Feature Specification: Volume profile confluence

**Feature Branch**: `exp-005-volume-confluence`

**Created**: 2026-09-09

**Input**: REQ-EXP-005 — "does boundary overlap with VAH/VAL/HVN/LVN materially
change target-before-stop probability?" Criteria derived on 2026-09-09.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Say which setups had confluence (Priority: P1)

A boundary sits on a value-area edge, on a volume node, or on neither.

**Why this priority**: the two populations are the experiment. A
misclassification moves setups between them and every number after that is about
a different question.

**Acceptance Scenarios**:

1. **Given** a boundary inside a high-volume node, **When** it is classified, **Then** it is confluent and the node's kind is named.
2. **Given** a boundary at the value-area high, **When** it is classified, **Then** it is confluent on the edge.
3. **Given** a boundary where nothing traded, **When** it is classified, **Then** it is not confluent.
4. **Given** a configured band, **When** it is widened, **Then** a boundary just off an edge joins the confluent population.

---

### User Story 2 - Answer the question, including "no" (Priority: P1)

Target-before-stop probability for each population, and a verdict against a
declared effect size.

**Why this priority**: "materially" is the word the question turns on, and an
effect size chosen after seeing the difference is not a finding.

**Acceptance Scenarios**:

1. **Given** a higher probability with confluence than without, and a difference above the effect size, **When** the verdict is read, **Then** it is "higher".
2. **Given** a lower one, **When** the verdict is read, **Then** it is "lower".
3. **Given** a difference below the effect size, **When** the verdict is read, **Then** it is "not materially different".
4. **Given** the same difference and a larger effect size, **When** the study is rerun, **Then** the verdict changes.
5. **Given** the study's signature, **When** it is inspected, **Then** the effect size has no default.

---

### User Story 3 - Refuse what cannot be answered (Priority: P1)

Populations too small, or with nothing decided, are refusals rather than numbers.

**Why this priority**: a difference over three setups is noise with a decimal
point, and it reads exactly like a result.

**Acceptance Scenarios**:

1. **Given** a population below the configured minimum, **When** the study runs, **Then** it is refused and the population is named.
2. **Given** a population where every setup timed out, **When** the study runs, **Then** it is refused rather than reporting a probability of zero.
3. **Given** ambiguous outcomes, **When** the study runs, **Then** they are excluded and counted.
4. **Given** timeouts, **When** the probability is computed, **Then** they are counted but are not decisions.

---

### Edge Cases

- What happens when a boundary is both on an edge and in a node? It is confluent once. The populations are two, not four.
- What happens when the effect size is zero? Any non-zero difference is material, which is a legitimate declaration and a very strict one.
- What happens when both populations have identical probabilities? The difference is zero, which is below every non-negative effect size, so the answer is "not materially different".
- What happens when a price falls in no bin at all? It is not a node — nothing traded there to be a low-volume one — and not an edge unless it is within the band of one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A boundary MUST be classified as confluent when it lies within a configured band of the value-area high or low, or inside a volume node.
- **FR-002**: The node's kind MUST be reported when there is one.
- **FR-003**: The band MUST be configuration.
- **FR-004**: Target-before-stop probability MUST be computed over setups that reached a target or a stop.
- **FR-005**: Timeouts MUST be counted and MUST NOT be decisions.
- **FR-006**: Ambiguous outcomes MUST be excluded and counted.
- **FR-007**: The verdict MUST be one of higher, lower, or not materially different.
- **FR-008**: The effect size MUST be a required argument with no default.
- **FR-009**: A population below a configured minimum MUST refuse, naming which.
- **FR-010**: A population that decided nothing MUST refuse rather than report zero.
- **FR-011**: A negative effect size MUST be refused.

### Key Entities

- **Confluence**: whether a boundary sits on an edge, a node, or neither.
- **Population**: one side's setups, targets, stops and timeouts.
- **Result**: both populations, the difference, the effect size and the verdict.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A node boundary, an edge boundary and a boundary on neither each classify correctly.
- **SC-002**: Widening the band moves a boundary into the confluent population.
- **SC-003**: All three verdicts are produced by constructed populations.
- **SC-004**: The same difference flips the verdict when the effect size changes.
- **SC-005**: The effect size has no default, verified over the signature.
- **SC-006**: A small population refuses, naming which side.
- **SC-007**: A population with nothing decided refuses.
- **SC-008**: Ambiguous outcomes are excluded and counted.
- **SC-009**: Timeouts are counted and excluded from the denominator.
- **SC-010**: A negative effect size refuses.

## Assumptions

- **Outcomes are supplied**, resolved by [[REQ-BT-001]]. This study compares populations; it does not decide what happened to a setup.
- **The classification is point-in-time by construction**: the profile passed in is the one that existed at signal time, and a study handed a later profile is asking a different question.
- **Two populations, not four.** A boundary on both an edge and a node is confluent once; separating the kinds is a finer question than EXP-005 asks.
