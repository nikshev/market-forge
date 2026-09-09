---
traces: [REQ-US-006]
status: draft
---

# Feature Specification: An ablation across feature families

**Feature Branch**: `us-006-ablation`

**Created**: 2026-09-09

**Input**: REQ-US-006 — "an ablation report exists comparing: channel only;
channel + order flow; channel + derivatives; channel + DEX; all combined." PRD
§25.6's "ablation by feature family", and the instruction at EXP-015: "use strict
ablation and same walk-forward folds".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask what each family is worth (Priority: P1)

Five arms, each fitted and scored on the same folds, reported together.

**Why this priority**: REQ-US-006 names the five arms. The question is what the
order-flow, derivatives and DEX families add over the channel alone, and it can
only be answered by holding everything else fixed.

**Acceptance Scenarios**:

1. **Given** labelled rows and the five arms, **When** the ablation runs, **Then** every arm has a score against the same baselines.
2. **Given** the arms, **When** the report is read, **Then** all five appear — each as a result or as an explicit absence.
3. **Given** one fold set, **When** the arms run, **Then** every arm is scored on identical folds.
4. **Given** an arm with more families than another, **When** both run, **Then** the difference between their scores is attributable to those families alone.
5. **Given** one input, **When** the ablation runs twice, **Then** the two reports are equal.

---

### User Story 2 - Never report an arm that was not really run (Priority: P1)

An arm whose extra families contributed no features is reported as not run, with
the reason.

**Why this priority**: the registry carries order-flow and derivatives features
today, and no channel or DEX ones. "Channel + DEX" over rows with no DEX
features is "channel only" wearing another name — and reported as a result it
says the DEX family adds nothing, which is a finding about the data pipeline
presented as a finding about the market.

**Acceptance Scenarios**:

1. **Given** an arm whose families match no available feature, **When** the ablation runs, **Then** it is reported as not run, with the reason.
2. **Given** two arms that resolve to the same feature set, **When** the ablation runs, **Then** the second is reported as a duplicate of the first rather than as an independent comparison.
3. **Given** an arm that is not run, **When** the report is ranked, **Then** it does not appear in the ranking.
4. **Given** every arm unrunnable, **When** the ablation runs, **Then** the report says so rather than returning an empty ranking that reads like a completed comparison.

---

### Edge Cases

- What happens when the "channel only" arm itself has no features? Every arm is a duplicate of it or unrunnable, and the report says the ablation could not be run. An ablation with no baseline arm has nothing to be an ablation against.
- What happens when an arm's features exist but its target never occurs in a fold? The fold is dropped with its reason, as the direct baseline already does, and the arm is scored on the folds that remain.
- What happens when two arms tie exactly? They rank by score and then by name, so the order is the same on two runs.
- What happens when a family is named that the taxonomy does not know? It is refused at construction rather than resolving to nothing, which would look like an arm with no data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An arm MUST name the feature families it includes, and an unknown family MUST be refused.
- **FR-002**: The five arms REQ-US-006 names MUST be defined and MUST all appear in the report.
- **FR-003**: Every arm MUST be scored on the same folds, and the report MUST state how many folds that was.
- **FR-004**: An arm whose resolved feature set is empty MUST be reported as not run, with the reason.
- **FR-005**: An arm whose feature set equals an earlier arm's MUST be reported as a duplicate of it, naming that arm.
- **FR-006**: An arm reported as not run or duplicate MUST NOT appear in the ranking.
- **FR-007**: The ranking MUST be by score, ties broken by arm name.
- **FR-008**: A report with no runnable arm MUST say so rather than present an empty ranking.
- **FR-009**: Each arm's score MUST be produced by the same scoring path the direct baseline uses, not a second one.
- **FR-010**: One input MUST produce one report.
- **FR-011**: No module may consult a system clock or a random source.

### Key Entities

- **Arm**: a name and the feature families it includes.
- **Ablation report**: one entry per arm — a result, a duplicate, or a stated absence — the ranking, and the folds every arm shared.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All five arms appear in the report.
- **SC-002**: Every scored arm ran on the same folds, verified by count and by identity.
- **SC-003**: An arm with no features for its families is reported as not run.
- **SC-004**: An arm identical to an earlier one is reported as a duplicate naming it.
- **SC-005**: Neither appears in the ranking.
- **SC-006**: A report with nothing runnable says so.
- **SC-007**: Two runs over one input produce equal reports.
- **SC-008**: An unknown family refuses.
- **SC-009**: No module references a clock or a random source.

## Assumptions

- **The rows are supplied.** Building a point-in-time dataset is [[REQ-WP-017]]'s work; this compares feature sets over one.
- **The taxonomy maps REQ-US-006's user-facing groups onto the feature registry's families.** The registry carries `order_book`, `order_flow`, `trade_flow`, `volume_structure` and `derivatives` today, and no `channel` or `dex` family — which is exactly why FR-004 exists.
- **The model is the direct logistic baseline**, as [[REQ-WP-019]]'s direct target uses. An ablation comparing arms under different models would measure the models.
