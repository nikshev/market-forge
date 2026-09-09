---
traces: [REQ-EXP-014]
status: draft
---

# Feature Specification: Order-flow exhaustion around extrema

**Feature Branch**: `exp-014-exhaustion`

**Created**: 2026-09-09

**Input**: REQ-EXP-014 — a conditional study around future-labelled extrema, repeated point-in-time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Study every order-flow signal around a labelled turn (Priority: P1)

OFI sign and slope; CVD divergence; microprice deviation; spread widening; wall
replenishment/cancellation; absorption.

**Why this priority**: the conditional study is the question everyone asks
first — what does the book do at a top? — and it is a real question with a real
answer.

**Acceptance Scenarios**:

1. **Given** the six bullets, **When** the study runs, **Then** each has an entry.
2. **Given** a signal, **When** its conditional entry is read, **Then** it says it is retrospective.
3. **Given** control bars, **When** they are chosen, **Then** none of them sits within the gap of a turn.
4. **Given** a signal not supplied, **When** the study runs, **Then** it is refused rather than read as zeros.

---

### User Story 2 - Repeat it point-in-time (Priority: P1)

The same signals, at the moment of the decision, against a turn inside a
horizon.

**Why this priority**: EXP-014's own second sentence, and the only part of it
that could ever change what anyone does. Everything in the first study happened
already.

**Acceptance Scenarios**:

1. **Given** any signal, **When** the predictive entry is read, **Then** it carries a base rate, a precision and a lift.
2. **Given** a bar being decided, **When** its calling threshold is computed, **Then** no bar at or after it was read — the threshold included.
3. **Given** a bar whose horizon runs past the end of the series, **When** the study runs, **Then** it is not decided.
4. **Given** a signal that never stands out, **When** its precision is read, **Then** it is absent rather than zero.
5. **Given** a call exactly `horizon` bars before a turn, **When** it is scored, **Then** it is a hit; one bar earlier is not.

---

### User Story 3 - Say which signals explain and which forecast (Priority: P1)

Four readings: explains and predicts, explains only, predicts only, neither.

**Why this priority**: this is the confusion EXP-014 names. A signal extreme
around every top and flat at every decision would top the conditional table and
be worth nothing.

**Acceptance Scenarios**:

1. **Given** a signal high only after each turn, **When** it is read, **Then** it explains and does not forecast, and the report lists it as such.
2. **Given** a signal high before each turn, **When** it is read, **Then** it does both.
3. **Given** a signal on a period no turn follows, **When** it is read, **Then** it is neither.
4. **Given** the report, **When** its note is read, **Then** it says the conditional arm's numbers are not evidence for the predictive question.

---

### Edge Cases

- What happens when a series is too short for any bar to have both a trailing distribution and a full horizon? The study refuses rather than reporting that it found nothing.
- What happens when a signal sits at one value most of the time? Its quantile *is* that value, and "at or above" would call every bar; the call is strictly above.
- What happens when a labelled extremum falls outside the series? Refused.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All six PRD bullets MUST be studied; "OFI sign and slope" MUST be two columns.
- **FR-002**: The conditional arm MUST use a window straddling each turn and MUST declare itself retrospective.
- **FR-003**: Control bars MUST sit outside a configured gap from every turn.
- **FR-004**: The predictive arm MUST read no bar at or after the bar being decided, including the calling threshold.
- **FR-005**: The predictive arm MUST decide only bars with a full horizon ahead of them.
- **FR-006**: A call MUST be strictly above the trailing quantile.
- **FR-007**: The horizon MUST include its own last bar and MUST NOT reach backwards.
- **FR-008**: Precision over no calls MUST be absent, not zero.
- **FR-009**: Both arms MUST be reported for every signal, separately.
- **FR-010**: The reading MUST name which of the four cases a signal is in, and the report MUST list the signals that explain without forecasting.
- **FR-011**: The forecast floor MUST sit above a lift of one.
- **FR-012**: A missing series MUST be refused; an extremum outside the series MUST be refused.
- **FR-013**: The research judgements MUST be required arguments.
- **FR-014**: The report MUST be deterministic.

### Key Entities

- **Contemporaneous**: the conditional arm's counts, means and effect size, with its retrospective declaration.
- **Predictive**: the point-in-time arm's decided bars, calls, hits, base rate, precision and lift.
- **Reading rule**: what counts as explaining, and what counts as forecasting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Six bullets, seven signals, one entry each.
- **SC-002**: Every conditional entry declares itself retrospective, and the note says why it matters.
- **SC-003**: The control count equals the bars outside every turn's gap.
- **SC-004**: The calls over a prefix equal the calls the whole series makes at those bars, on a series whose halves differ.
- **SC-005**: Decided bars equal the series less the horizon and the warm-up.
- **SC-006**: A binary signal is called on its high bars, not on all of them.
- **SC-007**: A call `horizon` bars ahead hits; `horizon + 1` ahead does not.
- **SC-008**: A signal that never stands out has absent precision and lift.
- **SC-009**: A signal high only after the turns reads as explaining without forecasting, and appears in the report's list.
- **SC-010**: A signal high before the turns reads as doing both.
- **SC-011**: A signal on an unrelated period reads as neither, even with a lift above one.
- **SC-012**: The two arms disagree on the same pair of series.
- **SC-013**: A short series, a missing signal and an out-of-range extremum are each refused.
- **SC-014**: Omitting a research judgement raises; a quantile outside `(0, 1)` raises; a lift floor at one raises.
- **SC-015**: Two runs produce equal reports.

## Assumptions

- **The extrema are supplied, already labelled.** Labelling them is [[REQ-WP-019]]'s job and this study takes its output.
- **The signals are supplied as series.** Computing them is the feature registry's job; a study that recomputed them would be testing the computation rather than the question.
- **The conditional arm is allowed to be retrospective.** PRD §13A.6 permits exactly this use for a retrospective reference, and the requirement is that it says so.
