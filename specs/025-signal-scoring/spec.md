---
traces: [REQ-SCORE-001]
status: draft
---

# Feature Specification: Deterministic signal score, explainability and the alert ranker

**Feature Branch**: `score-001-signal-scoring`

**Created**: 2026-09-09

**Input**: REQ-SCORE-001 — PRD §22.1 to §22.4 and §43. Extracted because
[[REQ-US-001]] and [[REQ-US-004]] both need a score no requirement covered.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Score a setup the same way twice (Priority: P1)

Six feature groups, each capped as PRD §22.1 caps it, summed to a raw score and
multiplied by a data quality figure.

**Why this priority**: §22.2 gives a worked example with every intermediate
number. A scoring engine that cannot reproduce it is not the one the PRD
describes.

**Acceptance Scenarios**:

1. **Given** §22.2's six group contributions and its 0.96 multiplier, **When** the score is computed, **Then** the raw score is 81 and the final score is 77.8.
2. **Given** a contribution above its group's cap, **When** the score is computed, **Then** it is refused, not clipped.
3. **Given** one set of inputs, **When** the score is computed twice, **Then** the two results are equal.
4. **Given** a group named that §22.1 does not list, **When** the score is computed, **Then** it is refused.
5. **Given** a data quality multiplier outside `[0, 1]`, **When** the score is computed, **Then** it is refused.

---

### User Story 2 - Tell a missing family from a bad one (Priority: P1)

A family with no data is recorded as missing and lowers confidence; it never
scores zero.

**Why this priority**: §22.1's own sentence — "Missing family must not
automatically equal zero; score should account for data availability with
explicit confidence downgrade." A missing DeFi family scored as zero is a
10-point penalty for an outage.

**Acceptance Scenarios**:

1. **Given** a family with no data, **When** the score is computed, **Then** the family is listed as missing and does not contribute zero.
2. **Given** a missing family, **When** the score is computed, **Then** the confidence is lower than with every family present, and by how much is readable.
3. **Given** two runs, one with a family missing and one with that family scoring zero on real data, **When** their scores are compared, **Then** they differ.
4. **Given** every family missing, **When** a score is requested, **Then** it is refused — there is nothing to score.

---

### User Story 3 - Say why a signal got its score (Priority: P1)

Top positive factors, top negative factors, missing factors, the raw feature
snapshot, and the version of the model that scored it.

**Why this priority**: §22.4 lists all five, and PRD §0 item 10 requires being
able to explain why a signal received its score.

**Acceptance Scenarios**:

1. **Given** a computed score, **When** an explanation is built, **Then** it carries top positive factors, top negative factors, missing factors, the raw feature snapshot and the model version.
2. **Given** a score, **When** its explanation is read, **Then** every one of §22.1's six groups appears either as a contribution or as an explicit absence.
3. **Given** no computed score, **When** an explanation is requested, **Then** it is refused.
4. **Given** two groups with equal contribution, **When** the top factors are listed, **Then** the order is a declared tie-break rather than input order.

---

### User Story 4 - Rank many setups against each other (Priority: P2)

`rank_score = setup_score * data_quality * liquidity_factor * novelty_factor`.

**Why this priority**: §43, and [[REQ-US-001]]'s sorted market list is built on
it.

**Acceptance Scenarios**:

1. **Given** the four factors, **When** the rank score is computed, **Then** it is their product.
2. **Given** a factor outside `[0, 1]`, **When** the rank score is computed, **Then** it is refused.
3. **Given** several candidates, **When** they are ranked, **Then** the order is by rank score descending, with equal scores broken by a declared key.
4. **Given** a candidate whose liquidity factor is zero, **When** it is ranked, **Then** its rank score is zero — an illiquid asset does not reach the top on setup quality alone.

---

### User Story 5 - Put the alert threshold in configuration (Priority: P2)

`score >= 75` by default, resolvable per symbol, timeframe and setup type.

**Why this priority**: §22.3 says "configurable per symbol/timeframe/setup" and
calls 75 a "default research value only". A constant would make it neither.

**Acceptance Scenarios**:

1. **Given** no override, **When** a threshold is resolved, **Then** it is 75, and the value declares itself a research default.
2. **Given** an override for a symbol and timeframe, **When** a threshold is resolved for them, **Then** the override applies.
3. **Given** overrides at different specificities, **When** one is resolved, **Then** the most specific match wins, deterministically.
4. **Given** a threshold outside `[0, 100]`, **When** it is configured, **Then** it is refused.

---

### Edge Cases

- What happens when every family is missing? The score is refused. A score computed from nothing is not a low score, and reporting one would put an empty setup on the same axis as a weak one.
- What happens when a contribution is negative? Refused. §22.1's groups are `0..cap`; a negative contribution is a different scoring scheme.
- What happens when the data quality multiplier is zero? The final score is zero, and that is correct — §43 says data quality "penalizes stale/missing sources", and a source that is entirely stale carries no signal.
- What happens when two candidates tie on rank score? They order by a declared key. Ranking by input order would make the list depend on how it was assembled.
- What happens to a group present but scoring genuinely zero? It contributes zero and is *not* listed as missing. That distinction is the whole point of the missing-family rule.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The six groups and their caps MUST be exactly PRD §22.1's, and a group outside that set MUST be refused.
- **FR-002**: A contribution above its group's cap or below zero MUST be refused, never clipped.
- **FR-003**: The raw score MUST be the sum of the present groups' contributions, normalized to `[0, 100]` over the caps that were observable.
- **FR-004**: The final score MUST be the raw score times the data quality multiplier, which MUST lie in `[0, 1]`.
- **FR-005**: §22.2's worked example MUST reproduce exactly: 81 raw, 0.96 multiplier, 77.8 final.
- **FR-006**: A missing family MUST be recorded as missing, MUST NOT contribute zero, and MUST lower a reported confidence.
- **FR-007**: A score with no present family MUST be refused.
- **FR-008**: Scoring MUST be deterministic: one input, one result.
- **FR-009**: An explanation MUST carry top positive factors, top negative factors, missing factors, the raw feature snapshot and the model version.
- **FR-010**: Every one of the six groups MUST appear in an explanation, as a contribution or as an explicit absence.
- **FR-011**: An explanation MUST NOT be constructible without a computed score.
- **FR-012**: `rank_score` MUST be `setup_score * data_quality * liquidity_factor * novelty_factor`, with the three factors bounded to `[0, 1]`.
- **FR-013**: Ranking MUST be total and stable, with ties broken by a declared key.
- **FR-014**: The alert threshold MUST be configuration with a default of 75, labelled a research default, resolvable per symbol, timeframe and setup type, most-specific first.
- **FR-015**: No module may consult a system clock.

### Key Entities

- **Group contribution**: one of §22.1's six groups, its value, its cap and the named factors behind it.
- **Signal score**: raw, final, the multiplier, the groups that contributed, the families that were missing, and a confidence.
- **Explanation**: §22.4's five items.
- **Ranked candidate**: a rank score and the four factors it came from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: §22.2's example reproduces to the decimal.
- **SC-002**: An over-cap or negative contribution refuses.
- **SC-003**: A missing family is distinguishable from a family scoring zero, in both the score and the explanation.
- **SC-004**: A score with nothing present refuses.
- **SC-005**: One input scores identically twice.
- **SC-006**: An explanation carries all five of §22.4's items and all six groups.
- **SC-007**: An explanation cannot be built without a score.
- **SC-008**: `rank_score` matches the formula, and an out-of-range factor refuses.
- **SC-009**: Ranking is stable across two runs over the same set in different input orders.
- **SC-010**: The threshold defaults to 75, declares itself a research value, and resolves most-specific-first.
- **SC-011**: No module references a system clock.

## Assumptions

- **Group contributions are supplied, not computed here.** Each family's arithmetic already lives in its own package — channel quality in `channels`, order flow in `features`, volume in `volume`, derivatives in `derivatives`, DeFi and cross-venue in `dex` and `crossvenue`. This engine combines them, and a caller that supplies them can be read at the call site.
- **The data quality multiplier is supplied.** §43 defines what it penalizes; computing it needs source freshness this module does not hold.
- **§26.3's severity tiers are not built here.** They are a §26 alerting concern that reads a score; this requirement produces the score.
