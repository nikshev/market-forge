---
traces: [REQ-US-005]
status: draft
---

# Feature Specification: Backtesting one setup family at a time

**Feature Branch**: `us-005-setup-families`

**Created**: 2026-09-09

**Input**: REQ-US-005 — "`upper_rejection_short` and `middle_continuation_short`
can each be backtested independently, as separate setup families." PRD §31's
`signals:` configuration block and §25.2's rule against a separate backtest
implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run one family and see only its setups (Priority: P1)

A backtest of `upper_rejection_short` opens upper-zone short candidates and no
others.

**Why this priority**: the machine tracks one candidate at a time. Without a
restriction, a middle-zone setup occupies it and the upper-zone setup that would
have opened two bars later never does — so a run "of" one family is measuring
its interference with another.

**Acceptance Scenarios**:

1. **Given** a family, **When** a backtest runs, **Then** every candidate it opens belongs to that family.
2. **Given** bars that would open both families, **When** each is run separately, **Then** each run's candidate count is unaffected by the other family's setups.
3. **Given** a family, **When** the report is read, **Then** it names the family that produced it.
4. **Given** no family, **When** a backtest runs, **Then** it behaves exactly as it does today and the report names no family.

---

### User Story 2 - Configure a family the way the PRD configures one (Priority: P2)

A family carries the thresholds PRD §31 lists for it, and two families differ in
their configuration rather than in code.

**Why this priority**: §31's block gives each family its own quality floor, zone
start and tolerance. Families that differed only by name would make "backtest
them separately" a distinction without a difference.

**Acceptance Scenarios**:

1. **Given** the two families, **When** their configurations are read, **Then** each carries its own quality floor, zone and tolerance.
2. **Given** `upper_rejection_short`, **When** its configuration is read, **Then** it holds PRD §31's own numbers.
3. **Given** a family, **When** its report's configuration is read, **Then** the thresholds it ran under are in it.
4. **Given** a family whose zone bounds are inverted or outside `[0, 1]`, **When** it is constructed, **Then** it is refused.

---

### Edge Cases

- What happens when a family's zone never triggers on the given bars? The report says zero candidates opened, which is a result. It is distinguishable from a run that could never look, because the skipped-bar count is separate.
- What happens when two families are run over one set of bars? Two reports, each naming its family. Nothing merges them; a combined figure would be a third family nobody configured.
- What happens to a candidate already open when a family's zone stops matching? Nothing changes: a family restricts what may *open*, not how a live candidate progresses. Abandoning a candidate mid-lifecycle would report an invalidation that the engine never made.
- What happens when a family names a boundary and direction the engine never pairs? It opens nothing, and the report's zero says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A setup family MUST name the boundary and direction it opens, and its thresholds.
- **FR-002**: A backtest of a family MUST open only that family's candidates.
- **FR-003**: A family MUST NOT affect how an already-open candidate progresses.
- **FR-004**: A report MUST name the family it ran, and MUST name none when no family was given.
- **FR-005**: Running with no family MUST behave as the runner does today.
- **FR-006**: `upper_rejection_short` MUST carry PRD §31's stated numbers.
- **FR-007**: A family's thresholds MUST appear in its report's configuration.
- **FR-008**: A family with an inverted zone, or one outside `[0, 1]`, MUST be refused.
- **FR-009**: The two families MUST be independently runnable over one bar series, and neither run's counts may depend on the other's.
- **FR-010**: No strategy logic may live in the family or the runner; both configure the production engine.

### Key Entities

- **Setup family**: a name, the boundary and direction it opens, and its thresholds.
- **Report**: as today, plus the family that produced it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A family's run opens only its own candidates, verified over bars that would open both.
- **SC-002**: Two families run over one series produce counts neither of which changes when the other is not run.
- **SC-003**: A report names its family; a family-less run names none.
- **SC-004**: `upper_rejection_short`'s configuration matches PRD §31.
- **SC-005**: An invalid zone refuses.
- **SC-006**: The runner's existing behaviour is unchanged when no family is given.
- **SC-007**: The family configures the production machine and adds no transition rule of its own.

## Assumptions

- **Both families already exist as candidate shapes.** The engine opens upper-zone shorts and middle-zone shorts today; what is missing is the family as a unit of configuration and reporting.
- **PRD §38's `channelflow backtest --strategy` CLI is unbuilt**, and no requirement covers it. This feature is the library-level capability that command would call.
- **§31's `confirmation_bars`, `min_score` and `cooldown_bars` are not family fields here.** The first is the engine's two-bar rule, the second belongs to [[REQ-SCORE-001]]'s threshold, and the third has no engine support — carrying them as fields nothing reads would describe behaviour that does not exist.
