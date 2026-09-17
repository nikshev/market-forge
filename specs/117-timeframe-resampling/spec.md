---
traces: [REQ-WP-073]
status: draft
---

# Feature Specification: Bars at every configured timeframe

**Feature Branch**: `wp-073-timeframe-resampling`

**Created**: 2026-09-17

**Status**: Draft

**Input**: [[REQ-WP-073]] — PRD §5.1 (Phase 1 timeframes), §31 (timeframes are
configuration), §29.4 (`bars` keyed by `(venue, symbol, timeframe, open_time)`),
§28.2 (`GET /api/v1/bars` takes `timeframe`).

## Context

The deployment writes one series: one-minute bars, because
`CHANNELFLOW_INGEST_TIMEFRAME_NS` is a single value and `BarBuilder` is "One
symbol, one timeframe". §5.1 names four timeframes and §31 makes the list
configuration, so one series is not the shape the PRD describes.

**Measured on the running stack, 2026-09-17.** `GET /api/v1/bars` at
`timeframe_ns=60000000000` returns final bars; the same request at
`900000000000` returns `{"bars":[]}`. Nothing is wrong with the data — the
fifteen-minute series was never produced by anything.

### Why resampling, and what it costs

The alternative is one `BarBuilder` per timeframe against the same trade stream,
which the builder's own docstring anticipates: "Composition of several is the
caller's." This specification takes the other path — assemble higher timeframes
from the stored one-minute rows — because it is idempotent, can be run over
history that has already been archived, and adds nothing to the socket-side
path that must keep up with a live feed.

The cost is a failure mode the trade-driven builder does not have. `BarBuilder`
closes a window when its watermark passes; it knows time moved on. A resampler
reads rows, and **a window missing three of its 240 minutes looks exactly like a
window that has all of them** unless something counts them. That is why
completeness is a stated, tested condition here and not an implementation
detail, and why [[REQ-NRT-UPSAMPLE]] exists as a non-waivable constraint over
this work.

### Two boundaries arithmetic gets wrong

Window assignment today is `(event_time_ns // timeframe_ns) * timeframe_ns` —
alignment to the Unix epoch. For 5m, 15m, 30m, 1h, 4h and 1d that is also the
UTC boundary, because each divides a day evenly.

- **A week does not.** 1 January 1970 was a Thursday, so epoch-aligned weekly
  windows open on Thursdays. A weekly bar opens Monday 00:00 UTC.
- **A calendar month is not a duration.** 28, 29, 30 or 31 days, so it has no
  `timeframe_ns` — the column is `int64` nanoseconds. `1M` is outside this
  feature, refused rather than approximated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A higher timeframe has a series (Priority: P1)

A reader asks §28.2 for a configured timeframe and receives final bars.

**Independent Test**: configure 5m over a one-minute series and ask for it. On
its own this delivers the whole point of the feature — a chart at a timeframe
other than one minute.

**Acceptance Scenarios**:

1. **Given** a contiguous one-minute series, **When** the reader asks for
   `timeframe_ns` of 5m, **Then** it receives bars whose windows tile the
   covered span and each of which is final.
2. **Given** the same series, **When** the reader asks for a timeframe nothing
   has produced, **Then** it receives an empty series rather than an error —
   absence of data is not a failure.

### User Story 2 - The values are the aggregation, exactly (Priority: P1)

**Independent Test**: one window whose minutes differ in every field, compared
field by field against the aggregation computed by hand in the test.

**Acceptance Scenarios**:

1. **Given** five one-minute bars, **When** they are resampled to one 5m bar,
   **Then** `open` is the first minute's open, `high` the maximum high, `low`
   the minimum low, `close` the last minute's close, and `volume_base`,
   `volume_quote`, `trade_count` and `aggressive_buy_base` are the sums.
2. **Given** minutes whose highs and lows do not occur in the first or last
   minute, **Then** the extremes still come from the minutes that hold them —
   an implementation reading only the ends fails this.

### User Story 3 - A timeframe is added by configuration (Priority: P2)

**Independent Test**: configure 4h — a timeframe outside §5.1's four, which no
existing test data uses — and find its series produced with no code changed.

**Acceptance Scenarios**:

1. **Given** a configuration naming 30m, 4h, 1d and 1w, **When** resampling
   runs, **Then** each has a series.
2. **Given** a configuration naming a timeframe that is not a whole multiple of
   the source, **Then** it is refused with a reason, because its windows cannot
   tile the source series.

### User Story 4 - Running it again changes nothing (Priority: P2)

**Independent Test**: run resampling twice over one unchanged source and compare
the table before and after.

**Acceptance Scenarios**:

1. **Given** a table already holding resampled bars, **When** resampling runs
   again over the same source rows, **Then** no row is added, removed or
   altered.

### Edge Cases

- **A window missing one or more source minutes** produces no bar, and the
  refusal names the window and what was missing. This is [[REQ-NRT-UPSAMPLE]]'s
  condition; this feature must not satisfy it by emitting a bar computed from
  the minutes that happened to be present.
- **A window still in progress** produces no bar, however complete the minutes
  so far look.
- **A weekly window containing a Thursday** opens on the preceding Monday, not
  on that Thursday.
- **A missing minute that arrives later** may complete its window and produce
  the bar then. This is not an amendment — no bar for that window was ever
  published, so Constitution III and [[ADR-005]] are untouched.
- **`1M` requested** is refused with a reason naming the calendar-month problem.
  Neither silently accepted as 30 days nor silently dropped.
- **A source series with no rows at all** produces no bars and no error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST produce a bar series for each configured timeframe,
  assembled from the one-minute series for the same venue and symbol.
- **FR-002**: The set of timeframes MUST come from configuration. No component
  may carry the set as a constant — not the producer, not the read API, not the
  frontend.
- **FR-003**: A resampled bar's fields MUST equal the aggregation of its source
  minutes as stated in User Story 2.
- **FR-004**: A higher-timeframe bar MUST be produced only when every source
  minute of its window is present and final.
- **FR-005**: An incomplete window MUST yield no bar and MUST produce a refusal
  that names the window and what was missing, visible to the caller.
- **FR-006**: Windows at 5m, 15m, 30m, 1h, 4h and 1d MUST open on UTC
  boundaries; a weekly window MUST open Monday 00:00 UTC.
- **FR-007**: A configured timeframe that is not a whole multiple of the source
  timeframe MUST be refused with a reason.
- **FR-008**: `1M`, or any calendar-defined period, MUST be refused with a reason
  naming the calendar-month problem.
- **FR-009**: Resampling MUST be idempotent over unchanged source rows.
- **FR-010**: Every bar produced MUST carry `is_final`, and no non-final bar may
  be written — the existing rule of the `bars` table, restated because this
  producer is new.

### Key Entities

- **Source series**: the one-minute bars for one `(venue, symbol)`, as written by
  the ingest daemon.
- **Window**: a half-open interval `[s, s + T)` at timeframe `T`, whose opening
  instant is determined by `T`'s alignment rule.
- **Timeframe configuration**: the list of timeframes this deployment produces,
  per §31's `timeframes:` list.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every configured timeframe, a reader asking for it over a span
  covered by complete source minutes receives a bar for every window in that
  span — zero missing, zero extra.
- **SC-002**: Zero bars are produced for windows that are incomplete or in
  progress, measured by asking for every window boundary in a series with
  deliberately removed minutes.
- **SC-003**: Adding a timeframe requires changing configuration only, measured
  by the diff needed to add 4h: no source file changes.
- **SC-004**: A second resampling pass over unchanged input changes zero rows.
- **SC-005**: A chart opened at each configured timeframe shows candles rather
  than a failed load — the outcome a reader of this system actually sees.

## Assumptions

- The source is the one-minute series written by [[REQ-WP-066]]'s daemon. This
  feature does not introduce a second source, and does not resample from a
  higher timeframe to a higher one still — every timeframe is built from
  minutes, so an error cannot compound across levels.
- Every configured timeframe is a whole multiple of one minute. FR-007 refuses
  anything else rather than assuming it.
- All boundaries are UTC. §31's example configuration sets `timezone: UTC`, and
  no local-time boundary is in scope.
- `1M` is out of scope by the decision recorded in [[REQ-WP-073]], not deferred
  silently. A later requirement may add calendar periods; it will need a key that
  an `int64` nanosecond column cannot provide.
- A window that could not be produced because a minute was missing may be
  produced later if that minute arrives. Nothing published is ever rewritten.
