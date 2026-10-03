---
traces: [REQ-NRT-UPSAMPLE]
status: draft
---

# Feature Specification: No unfinalized higher-timeframe close reaches a lower-timeframe consumer

**Feature Branch**: `125-no-unfinalized-upsample`

**Created**: 2026-10-03

**Status**: Draft

**Input**: [[REQ-NRT-UPSAMPLE]] — PRD §13A.17, closing sentence: "Do not upsample a higher-timeframe
future close into lower-timeframe features before that higher-timeframe bar is finalized."

## Context

[[REQ-WP-073]] built the resampler and is `implemented`. Its function `resample` already does the
two things this requirement leans on: a window still open yields neither a bar nor a refusal, and a
window that has closed but is short of minutes yields a `Refusal` that names the window, what was
expected and what was present. The deployment shows it working — the resample job's log lists
refused windows by name on every pass.

This requirement exists because "already does" is a claim about a function, and the requirement is a
claim about **a seam**: nothing anywhere may hand a higher-timeframe bar that has not finished to
something computing at an earlier instant. [[REQ-NRT-UPSAMPLE]] is `hard_gated`, so it cannot hold a
status past `specified` until a test says so, and the test has to be able to see the violation it
forbids.

### What reading the code and running it showed

Three probes of `resample` on a five-minute target over one-minute sources
(`specs/125-no-unfinalized-upsample/probe.py`), run before writing this:

| window handed to `resample` | bars | refusals | should be |
|---|---|---|---|
| minutes 0-4, each once, all final (control) | 1 | 0 | 1 bar |
| minutes 0, 1, 2, 3 and **3 again** — minute 4 missing | **1** | 0 | no bar, one refusal |
| minutes 0-4, all present, **one not final** | **1** | 0 | no bar, one refusal |

Both wrong rows are holes in the property the requirement states. Completeness is judged by
**how many** source bars a window holds (`len(window) != expected`), not by **which** minutes: a
duplicated minute stands in for a missing one, and a bar is computed from four of five. And the
source bars' `is_final` is never read, so a window containing a bar that may still change is folded.

**Neither happens on the deployment today.** The live `bars` table has 55,546 one-minute rows and
55,546 distinct keys: no duplicate exists to trigger the first, and the table refuses unfinalized
rows on write ([[ADR-005]]), which is what has kept the second out. Both are therefore *latent*: the
function's own contract is weaker than the property it is cited for, and what protects it is
somebody else's behaviour. `read_bars` does not deduplicate, so a duplicate row — a restarted ingest
re-emitting a minute — would reach `resample` as it is.

### The seam, and who is on the other side of it

A window's bar carries `close_time_ns = s + T`. The storage layer's as-of read filters on
`close_time_ns`, so a bar whose window had not closed at an instant is not returned for it. That is
the mechanism the requirement's "asking for the bar as of any instant inside the window returns
nothing" leans on, and nothing tests it with a resampled bar and a real table.

No component today consumes bars at more than one timeframe in one computation: §13A.17's extrema
hierarchy and its confluence features have no requirement note yet and no code. So the "consumer"
the requirement speaks of is, today, **the read path**: if every read of a higher timeframe as of
`t` is guaranteed to hold only bars that closed by `t`, then whatever consumes them later inherits
the guarantee. Stated as a property of the read path, it can be tested now and will still bind a
consumer written next year.

### What this is not

The extrema hierarchy and confluence features of §13A.17 are not here. Nor is the calendar month
(`1M`), which does not tile, nor any change to how the resample job schedules itself.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A window is a bar only if every one of its minutes is there, once, and final (Priority: P1)

**Why this priority**: the two holes above are in this story, and it is the only story in which
today's code is wrong rather than merely untested.

**Independent Test**: hand `resample` the three windows in the table above, plus a window with a
duplicate and nothing missing, plus a window with a non-final bar and a refusal reading.

**Acceptance Scenarios**:

1. **Given** a closed window holding four distinct minutes and one of them twice, **When** it is
   resampled, **Then** no bar is produced and one refusal names the window and the missing minute.
2. **Given** a closed window whose five minutes are all present and one is not final, **When** it
   is resampled, **Then** no bar is produced and the refusal says which minute was not final.
3. **Given** a closed window with each minute exactly once and all final, **When** it is
   resampled, **Then** one bar is produced, as today.
4. **Given** a closed window with a minute missing, **When** it is resampled, **Then** the refusal
   names the window, the number expected and what was missing — the property today's test covers,
   kept.

---

### User Story 2 - Nothing inside an open window can be read (Priority: P1)

**Why this priority**: it is the first half of the seam: what the table will hand out.

**Independent Test**: write a resampled five-minute bar to a real table, then ask for the series as
of each minute-boundary instant strictly inside its window, and at its close.

**Acceptance Scenarios**:

1. **Given** a stored higher-timeframe bar covering `[s, s + T)`, **When** the series is read as of
   any instant `t` with `s <= t < s + T`, **Then** the bar is absent.
2. **Given** the same bar, **When** it is read as of `s + T`, **Then** it is present.
3. **Given** the answer is produced by asking the table, not by comparing `close_time_ns` in the
   test, **Then** a change to how the table filters would fail the test.

---

### User Story 3 - A consumer computing at `t` never reads a bar that closes after `t` (Priority: P1)

**Why this priority**: the second half, and the only one stated as a property of the whole.

**Independent Test**: over a day of one-minute bars resampled to every configured timeframe and
stored, read every timeframe as of a set of instants `t` and check every bar returned closed at or
before `t`. The instants are every seventh minute of the day **and** the instant before, at and after
every window boundary of every timeframe up to a day: a leak shows at a boundary, and every minute of
the day would be 1,440 reads for no extra evidence.

**Acceptance Scenarios**:

1. **Given** all configured timeframes stored from one day of source bars, **When** every
   timeframe is read as of each `t`, **Then** no bar has `close_time_ns > t`.
2. **Given** a reader that bypasses the as-of argument, **When** the same check runs, **Then** it
   fails — so the property is the as-of read's and not an accident of the fixture.

---

### User Story 4 - A leaking resampler is caught, and named (Priority: P2)

**Why this priority**: "a constraint whose test has never seen the violation it forbids is a
constraint nobody has checked" ([[REQ-NRT-UPSAMPLE]]'s own words).

**Independent Test**: a mutation specification that introduces each leak into `resample` — emit the
window in progress, drop the completeness check, count instead of identify, ignore finality — and a
sweep that reports each as caught by a test.

**Acceptance Scenarios**:

1. **Given** a `resample` that emits a window still open at `now_ns`, **When** the suite runs,
   **Then** a test fails and the sweep names the mutation.
2. **Given** each of the other three leaks, **Then** the same.
3. **Given** a surviving mutation, **Then** the sweep refuses to pass without a recorded reason.

### Edge Cases

- A window with no source bars at all: no bar and no refusal, as today (nothing to refuse).
- A window containing bars of two series: out of scope — `resample` is called per series.
- A source bar belonging to another timeframe than declared: the caller's contract, not this one's.
- The first window of a series that starts mid-window: refused for the minutes it lacks, as today.
- An as-of instant exactly at `s + T`: the bar is present (closed at that instant).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A higher-timeframe bar for `[s, s + T)` MUST be produced only if every source minute
  of the window is present **exactly once** and **final**.
- **FR-002**: A closed window failing FR-001 MUST yield no bar and one refusal that names the
  window, the number expected and what was wrong (missing, duplicated, not final), returned to the
  caller and not only logged.
- **FR-003**: A window still open at `now_ns` MUST yield neither a bar nor a refusal.
- **FR-004**: Reading the series as of any instant strictly inside `[s, s + T)` MUST NOT return that
  window's bar; as of `s + T` it MUST.
- **FR-005**: For every timeframe and every instant `t`, a read as of `t` MUST NOT return a bar with
  `close_time_ns > t`.
- **FR-006**: A resampler that emits an open window, omits the completeness check, counts rather than
  identifies minutes, or ignores finality MUST be caught by the suite, each by name.
- **FR-007**: The suite for this requirement MUST run with no services and no network.
- **FR-008**: The tests for FR-001 and FR-002 MUST fail against today's code for the stated reason
  (the repository's RED discipline).

### Key Entities

- **Window**: `[s, s + T)` of a target timeframe, tiled by `T / source` source minutes.
- **Refusal**: the record that a closed window was not folded, with the window and the reason.
- **As-of read**: a read of a series restricted to what had closed by an instant.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Of the five window shapes in User Story 1 (complete; duplicate with a minute missing;
  one not final; one missing; open), the number producing a bar is exactly one, and the number
  producing a refusal is exactly three (today: three produce a bar).
- **SC-002**: Over a day of source bars and every configured timeframe, the count of bars returned
  as of `t` that close after `t` is zero at every instant tested (the set named in User Story 3).
- **SC-003**: Each of at least four deliberately leaking resamplers is caught and named by the
  mutation sweep; the number surviving without a recorded reason is zero.
- **SC-004**: The whole suite for this requirement runs in under one minute with no network.

## Assumptions

- Source bars arrive per series, per declared source timeframe.
- A refusal is reported by the existing report path; this change adds reasons, not a new channel.
- `resample`'s signature may gain nothing a caller must pass: finality and identity are read from the
  bars it is given.
- The hard gate (R5) is met by a test that has seen the violation, which is User Story 4's mutation.
