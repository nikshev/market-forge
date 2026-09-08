---
traces: [REQ-WP-010]
status: draft
---

# Feature Specification: Backtest v1

**Feature Branch**: `wp-010-backtest-v1`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-010 — virtual clock; bar replay; strategy reuse; reports.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Replay history through the live engine (Priority: P1)

A researcher feeds historical bars to the backtest and gets the candidates the
production signal engine would have produced — because it is the production
signal engine, driven by a virtual clock rather than a real one.

**Why this priority**: PRD §25.2 says the same production code should run in
replay, and to avoid a separate backtest implementation of strategy logic.
Constitution Principle VII says live and replay must be the same code. A
backtest with its own copy of the rules measures the copy.

**Independent Test**: Drive the signal machine directly over a bar series,
then run the backtest over the same series, and compare the candidate histories.
They must be identical.

**Acceptance Scenarios**:

1. **Given** a bar series, **When** the backtest replays it, **Then** the candidate histories match those from driving the live engine directly, transition for transition.
2. **Given** a bar series, **When** the backtest runs twice, **Then** the results are identical.
3. **Given** a bar series, **When** the backtest runs, **Then** no wall-clock time influences any result.
4. **Given** bars out of chronological order, **When** the backtest runs, **Then** they are replayed in event-time order.

---

### User Story 2 - See what a configuration produced (Priority: P1)

The run yields a report: how many candidates opened, how many reached
confirmation, and why the rest ended.

**Why this priority**: Equal to US1 — a replay whose results cannot be read is
not a backtest. This report is what makes zone bounds and quality thresholds
tunable, and PRD §13.11 is explicit that those defaults are unproven.

**Independent Test**: Run over a constructed series with a known number of
setups and check the counts.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the report is read, **Then** it gives the number of candidates opened, broken down by direction and boundary.
2. **Given** a completed run, **When** the report is read, **Then** it gives the confirmation rate and the count of each terminal reason.
3. **Given** a completed run, **When** the report is read, **Then** it names the configuration that produced it.
4. **Given** two runs under different configurations, **When** their reports are compared, **Then** the difference in candidate counts is visible.

---

### User Story 3 - Trust that the clock is virtual (Priority: P2)

Every timestamp in the run comes from the data. Running the same backtest
tomorrow gives the same answer as running it today.

**Why this priority**: Below the two above only because its failure is caught by
them — a backtest consulting the wall clock would break US1's parity test on the
second run. Stated separately because PRD §25.2 names the virtual clock
explicitly.

**Independent Test**: Assert no module in the backtest package reaches for a
system clock.

**Acceptance Scenarios**:

1. **Given** the backtest package, **When** its source is inspected, **Then** no module imports a system clock.
2. **Given** a run, **When** its reported time range is read, **Then** it comes from the bars.

---

### Edge Cases

- What happens when the bar history is shorter than the channel lookback? No channel can be fitted, so no candidate opens, and the report says how many bars were skipped for that reason rather than silently reporting zero setups.
- What happens when a bar series contains a gap? The backtest replays what it has. A gap is a property of the data, and inventing bars to fill it would be fabricating history.
- What happens when the configuration produces no candidates at all? A report with zeroes and the configuration that produced them — which is a useful result, not an error.
- What happens when the same bars are replayed with a different channel lookback? Different candidates, and the report names the lookback, so the two runs cannot be confused.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backtest MUST replay finalized bars in event-time order.
- **FR-002**: The backtest MUST drive the production signal machine and channel model, not a reimplementation of their logic.
- **FR-003**: All time MUST come from the bars. No module in the backtest package may consult a system clock.
- **FR-004**: The backtest MUST fit a channel at each bar using only bars at or before that bar.
- **FR-005**: Replaying the same bars MUST produce results identical to driving the live engine directly over them.
- **FR-006**: Two runs over the same input MUST produce identical reports.
- **FR-007**: The report MUST give the number of candidates opened, by direction and by boundary.
- **FR-008**: The report MUST give the confirmation rate and a count of each terminal reason.
- **FR-009**: The report MUST record the configuration that produced it, including channel lookback and every signal threshold.
- **FR-010**: The report MUST give the event-time range covered and the number of bars replayed.
- **FR-011**: The report MUST give the number of bars skipped for want of sufficient channel history.
- **FR-012**: The report MUST NOT contain returns, win rate, expectancy or any economic metric, per ADR-009.
- **FR-013**: The report MUST be immutable once produced.

### Key Entities

- **Replay run**: one pass over a bar series under one configuration.
- **Report**: what that pass produced — counts, rates, and the configuration that caused them.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A backtest over a bar series produces candidate histories identical to driving the signal machine directly over the same series.
- **SC-002**: Two runs over the same input produce identical reports.
- **SC-003**: No module in the backtest package references a system clock, verified over the source.
- **SC-004**: A run over a constructed series with a known number of setups reports that number.
- **SC-005**: Reports from two different configurations differ, and each names its own configuration.
- **SC-006**: A run whose history is too short to fit a channel reports the skipped bars rather than zero setups.
- **SC-007**: No economic metric appears in any report.

## Assumptions

- Bar replay only. PRD §25.1's event replay — trades, order-book deltas, on-chain events — needs the order-book service and microstructure features, which are not built.
- No costs, no fills, no returns. ADR-009 explains why: an economic figure without the costs PRD §41 rule 9 requires would be quoted without its caveat.
- The backtest consumes bars it is given. Loading them from storage is a later concern, and PRD §29.4's table does not exist yet.
- Walk-forward splitting is out of scope. PRD §25.7 defines it and §41 rule 10 governs it; this feature runs one pass over one series.
- The report is a value, not a file format. Rendering it is presentation.
