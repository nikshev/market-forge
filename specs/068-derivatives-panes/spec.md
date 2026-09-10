---
traces: [REQ-WP-030]
status: draft
---

# Feature Specification: Lower panes for the derivatives features

**Feature Branch**: `wp-030-derivatives-panes`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-030 — four more of PRD §27.3's panes, and the check that keeps the list honest.

## Context

[[REQ-WP-027]] built three of §27.3's nine panes and deferred four to Phase 3 in
writing. Phase 3's data is finished: `open_interest_usd`, `oi_change_5m`,
`funding_z`, `basis_bps` and `liquidation_imbalance_5m` are registered, and the
timeseries endpoint serves any registered feature.

So the four entries are trivial. **What is not trivial is that a pane can name a
feature nobody registers.** Such a pane renders "no readings of this feature"
forever — a message this application produces honestly for a real absence — and
a reader has no way to tell a typo from a quiet market. The list will grow to
nine and beyond, by people who are not looking at the registry.

This specification is therefore mostly about the check.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A reader can look at the derivatives (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the pane selector, **When** it is shown, **Then** open interest, funding, basis and liquidations are offered beside the order-flow panes.
2. **Given** a derivatives pane, **When** points carry its feature, **Then** it draws them.
3. **Given** the DEX panes, **When** the selector is shown, **Then** they are absent.

---

### User Story 2 - A pane cannot name a feature that does not exist (Priority: P1)

**Why this priority**: The only failure this change can introduce, and it is
invisible in the browser.

**Acceptance Scenarios**:

1. **Given** the pane list, **When** it is checked against the feature registry, **Then** every pane's feature is registered.
2. **Given** a pane added later with a misspelled feature, **When** the suite runs, **Then** it fails naming the feature.
3. **Given** the check, **When** it runs, **Then** it reads the real pane list rather than a copy.

---

### User Story 3 - The existing rules still hold (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a derivatives pane, **When** a point carries no value for it, **Then** the instant is a gap rather than a zero.
2. **Given** the same pane, **When** a value is zero, **Then** it is drawn.
3. **Given** no points, no readings, or a failed load, **Then** the three stay distinguishable.

### Edge Cases

- **A feature registered but never recorded.** The pane says "no readings of this feature", which is honest and will look like a bug to whoever opens it first. Named here rather than hidden.
- **A pane list that grows past the selector's width.** Out of scope; nine buttons is a layout question and not a correctness one.
- **A feature whose name changes in the registry.** The check fails, which is the point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Panes for open interest, funding, basis and liquidations MUST be offered.
- **FR-002**: Every pane's feature MUST be a registered feature name.
- **FR-003**: The check MUST read the pane list as the application defines it, not a copy.
- **FR-004**: A pane naming an unregistered feature MUST fail the suite, naming it.
- **FR-005**: DEX panes MUST remain absent.
- **FR-006**: Derivatives panes MUST obey the gap, zero and three-state rules unchanged.
- **FR-007**: What the existing panes do MUST be unchanged.

### Key Entities

- **Pane list**: the offered panes, and the single place they are defined.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The selector offers seven panes; four are the derivatives ones.
- **SC-002**: Every offered feature appears in the registry's exposed names.
- **SC-003**: Introducing an unregistered pane turns the suite red, naming the feature.
- **SC-004**: A missing value is absent from a derivatives pane's series; a zero is present.
- **SC-005**: Every existing pane test passes unchanged.

## Assumptions

- **The check lives in the Python suite**, because that is where the registry is. Reading the TypeScript pane list from there is the only place the two lists meet; a check on either side alone would compare a list against itself.
- **Nothing writes derivative features into the feature table yet.** The registry knows them and the endpoint serves what is there. That gap belongs to whoever wires the derivatives path, and this specification names it rather than depending on it.
