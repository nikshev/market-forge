---
traces: [REQ-US-001, REQ-US-004]
status: draft
---

# Feature Specification: A ranked market list and a signal's contribution factors

**Feature Branch**: `us-001-004-scored-markets`

**Created**: 2026-09-09

**Input**: REQ-US-001 ("markets sorted by setup score") and REQ-US-004
("contribution factors are shown"), both over [[REQ-SCORE-001]]'s score.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find the most interesting situations first (Priority: P1)

The market list arrives ordered, best setup first.

**Why this priority**: REQ-US-001 is the whole of it — "so that I can quickly
find the most interesting situations". A list a reader has to sort themselves
does not answer it.

**Acceptance Scenarios**:

1. **Given** markets with different setup scores, **When** the list is served, **Then** it is ordered by rank score, highest first.
2. **Given** a market with a high setup score on an illiquid asset, **When** the list is served, **Then** PRD §43's liquidity factor moves it down.
3. **Given** two markets with equal rank scores, **When** the list is served twice, **Then** the order is the same both times.
4. **Given** a market with no scored setup, **When** the list is served, **Then** it appears after every scored one and its score is null, not zero.
5. **Given** a filter by venue, **When** the list is served, **Then** the remaining markets are still ordered by rank score.

---

### User Story 2 - See why a setup scored what it did (Priority: P1)

A signal's detail carries its contribution factors, its missing families, its
raw feature snapshot and the model version.

**Why this priority**: REQ-US-004 names the five families a reader wants to see,
and PRD §22.4 lists the five things every signal stores.

**Acceptance Scenarios**:

1. **Given** a scored signal, **When** its detail is fetched, **Then** the response carries top positive factors, top negative factors, missing factors and the model version.
2. **Given** a signal whose DeFi family had no data, **When** its detail is fetched, **Then** DeFi appears among the missing, not among the negative factors.
3. **Given** a scored signal, **When** its detail is read, **Then** every one of §22.1's six groups is accounted for.
4. **Given** an unscored signal, **When** its detail is fetched, **Then** the explanation is null and the rest of the detail still returns.
5. **Given** a signal detail, **When** it is rendered, **Then** the outcome stays visually separate from the explanation, as §27.4 requires.

---

### Edge Cases

- What happens when no market has a score? The list returns in a declared order rather than an arbitrary one, and every score is null.
- What happens when a market's score exists but its confidence is low? It ranks on its score, and the confidence travels with it so the reader can discount it. Hiding a low-confidence setup would be a filter nobody configured.
- What happens when a signal's explanation is requested for a signal that does not exist? The same 404 the detail already returns — the explanation does not invent a signal.
- What happens when a family scored zero rather than being absent? It shows as a negative factor, not as missing. The two are different statements and the panel must not merge them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The market list MUST be ordered by PRD §43's rank score, highest first.
- **FR-002**: Ordering MUST be stable, with equal rank scores broken by a declared key.
- **FR-003**: A market with no scored setup MUST sort after every scored one, and its score fields MUST be null rather than zero.
- **FR-004**: A market's response MUST carry its setup score, its rank score and its confidence when it has them.
- **FR-005**: Filters MUST apply before ordering, and the filtered list MUST still be ordered.
- **FR-006**: A signal's detail MUST carry an explanation with §22.4's items when the signal was scored.
- **FR-007**: The explanation MUST account for all six of §22.1's groups, as contributions or as explicit absences.
- **FR-008**: A missing family MUST NOT appear among the negative factors.
- **FR-009**: An unscored signal's detail MUST still return, with a null explanation.
- **FR-010**: The API MUST compute no score of its own; it serves what the pipeline stored.
- **FR-011**: The rendered panel MUST show each of the six groups with its contribution or its absence, and MUST keep the later outcome separate from the explanation.

### Key Entities

- **Scored setup**: a market's latest score, the factors §43 ranks it by, and when it was scored.
- **Market row**: a market, and its scores when it has them.
- **Explanation payload**: §22.4's five items, serialized.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The market list is ordered by rank score, verified against a hand-computed order.
- **SC-002**: An illiquid market with a high setup score ranks below a liquid one with a lower score.
- **SC-003**: Two identical requests return identical orders.
- **SC-004**: An unscored market sorts last with null scores.
- **SC-005**: A filtered list is still ordered.
- **SC-006**: A scored signal's detail carries the explanation; an unscored one carries null.
- **SC-007**: A missing family appears among the missing and nowhere else.
- **SC-008**: All six groups are accounted for in the rendered panel.
- **SC-009**: The API adds no arithmetic of its own beyond ordering.

## Assumptions

- **The pipeline stores scores.** Computing a live score per market needs every family's features at once, which is pipeline work; the API reads what was stored, as it does for every other endpoint (REQ-API-001 FR-010).
- **One score per market**, its latest. A history of scores is §29 storage work.
- **The panel is a component, not a page.** REQ-WP-009's chart page is where a signal is already opened from a deep link.
