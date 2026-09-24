---
traces: [REQ-WP-077]
status: draft
---

# Feature Specification: Channels, signals and extrema produced for the running deployment

**Feature Branch**: `122-channel-production`

**Created**: 2026-09-24

**Status**: Draft

**Input**: [[REQ-WP-077]] — PRD §6.2 (MVP compose list missing worker), §25.1 (record_replay function), §29.6 (channel_snapshots table immutable append-only)

## Context

The MVP compose list in PRD §6.2 lists `api`, `worker`, `ingest-binance` — but the `worker` service has no container because [[REQ-PIPE-001]] chose a replay over a daemon. That was the right call for building the pipeline and it leaves a deployment with bars and nothing else.

**Measured on the running stack, 2026-09-17**: the `bars` table holds 133 rows and `channel_snapshots` holds **0**. Nine services run; none of them fits a channel. §29.6's table exists, §28.3's read serves it, the chart draws it — and nothing produces it.

### The code exists; nothing runs it

`channelflow.pipeline.replay` already holds both halves, and they are already separated the way this needs:

- `record_bars(trades, …)` aggregates trades into bars and writes them.
- `record_replay(bars, …)` — "Replay `bars` and write the channel snapshots and signals it produced" — reads bars and writes channel snapshots, signals, confirmed extrema and extremum candidates. Its own comment is explicit that "this function reads it and never writes it" of the `bars` table.

So the missing piece is not an algorithm. It is a process that reads the bars this deployment already has, at each configured timeframe, and calls the function that exists. This is the "deployment work" [[REQ-PIPE-001]] named and deliberately excluded.

### Why it depends on the resampler

`record_replay` fits a channel over the bars it is given, and a channel at 4h is a fit over 4h bars. Until [[REQ-WP-073]] produces those series, this process has one timeframe to work on. The two together are what makes a timeframe control ([[REQ-WP-074]]) show a channel at every position rather than at one.

### What must not be assumed

Every recorder in `replay.py` carries a watermark and skips what the table already covers, so repetition is already designed for. That is a property to **verify under this requirement's own conditions** — a loop running every few minutes over a growing series is not the same exercise as a single replay over a fixture — not a property to inherit on trust.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A channel appears on the chart (Priority: P1)

A reader opens `/chart/binance/BTCUSDT?tf=1h` and sees a channel fitted over the 1h bars, where before the chart showed only candles with no channel overlay.

**Why this priority**: This is the defect. Every other story is about how we get there.

**Independent Test**: Render the chart at a timeframe that has bars and verify the channel overlay appears with correct boundaries.

**Acceptance Scenarios**:

1. **Given** the deployment has 1h bars for BTCUSDT, **When** the reader opens the chart at `tf=1h`, **Then** the channel overlay renders with upper/lower bands matching the fitted channel.
2. **Given** the deployment has 15m bars for ETHUSDT, **When** the reader opens the chart at `tf=15m`, **Then** the channel overlay renders for 15m timeframe.

### User Story 2 - The link still works (Priority: P1)

An alert fires and sends a deep link `/chart/binance/BTCUSDT?tf=4h&at=...&signal=<uuid>`. The reader clicks it and the chart opens at 4h with the channel fitted over 4h bars.

**Why this priority**: The alert system is the primary way readers discover channels. If the link doesn't work, the alert system is broken.

**Independent Test**: Hit the deep link with a valid `tf` and verify the chart loads with the correct timeframe and channel.

**Acceptance Scenarios**:

1. **Given** a link carrying `tf=4h`, **When** the page loads, **Then** the chart requests 4h bars and draws the 4h channel.
2. **Given** a link with no `tf`, **When** the page loads, **Then** the chart opens at the documented default timeframe and renders its channel.

### User Story 3 - Multiple timeframes, one deployment (Priority: P2)

The deployment runs with three configured timeframes (1m, 5m, 1h). A pass runs and `channel_snapshots` receives rows for all three timeframes.

**Why this priority**: [[REQ-WP-073]] produces multiple timeframes; this feature must consume all of them, not just the ingested one.

**Independent Test**: Configure three timeframes, run one pass, verify all three `channel_snapshots` tables receive rows.

**Acceptance Scenarios**:

1. **Given** a deployment offering 1m, 5m, 1h configured, **When** the pass runs, **Then** `channel_snapshots` has rows for all three timeframes for the same venue/symbol.
2. **Given** a timeframe with no bars yet, **When** the pass runs, **Then** that timeframe is skipped and logged, not failed.

### User Story 4 - Idempotent re-runs (Priority: P2)

The process runs every 5 minutes. A second pass over unchanged bars writes **zero** new rows.

**Why this priority**: Constitution III and §29.6 require immutable append-only. A re-run must not duplicate data.

**Independent Test**: Run the process twice over the same bars, count rows before and after the second pass.

**Acceptance Scenarios**:

1. **Given** a pass just completed, **When** a second pass runs immediately, **Then** `channel_snapshots` row count is unchanged, `signals` row count is unchanged, `confirmed_extrema` and `extremum_candidates` are unchanged.
2. **Given** a pass over unchanged bars, **Then** the pass logs "no new data" and exits successfully.

### User Story 5 - Partial failure, rest continues (Priority: P2)

One timeframe's channel fit fails (e.g., numerical error). The pass logs the failure and continues with remaining timeframes.

**Why this priority**: The rule `maintenance_main` already follows this pattern; a single timeframe's failure must not block others.

**Acceptance Scenarios**:

1. **Given** 1h bars cause a numerical error, 15m and 4h are healthy, **When** the pass runs, **Then** 15m and 4h channels are written, 1h failure is logged with venue/symbol/timeframe.

### User Story 6 - Empty timeframe handled gracefully (Priority: P2)

A timeframe has no bars yet (e.g., 1w before a week has passed). The pass logs "no bars for 1w" and continues.

**Why this priority**: Don't fail the whole pass; the timeframe will have data later.

**Acceptance Scenarios**:

1. **Given** 1w timeframe configured but no 1w bars exist, **When** the pass runs, **Then** 1w is skipped with a log message, other timeframes proceed.

### User Story 7 - Signal reaches the table in final state only (Priority: P2)

A signal is alive across multiple bars. Only its final state is written to `signals` table — never intermediate states.

**Why this priority**: [[REQ-PIPE-001]] established this property; a loop invoking it far more often must not break it.

**Acceptance Scenarios**:

1. **Given** a signal opens at bar 1, updates at bars 2-5, confirms at bar 6, **When** the pass runs over bars 1-6, **Then** `signals` table has exactly one row for that signal, with its final confirmed state.

### Edge Cases

- **A timeframe with no bars.** Skipped with a log line naming the timeframe, not failed; it will have data on a later pass.
- **Bars too short to fit a channel.** When a timeframe's series exists but is shorter than the fit needs, the pass writes no snapshot for it and says so, without failing the pass.
- **New bars arrive mid-pass.** The ingest daemon keeps writing while the pass runs. Moments already recorded stay untouched (Constitution III); only genuinely new moments may add rows.
- **A pass crashes halfway.** The next pass resumes from the recorders' watermarks: no duplicate rows, no rewritten snapshots.
- **A signal alive across the pass boundary.** A candidate that opened but has not confirmed is not written prematurely; it is written once, in its final state, on the pass that sees it complete.
- **An extremum observed but not confirmed.** The candidate is recorded; the confirmation is recorded later. Neither row is ever amended.
- **Configuration changes between passes.** A newly configured timeframe is processed; a removed one is left untouched — the pass never deletes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run a periodic pass that reads bars for each configured `(venue, symbol, timeframe)` and calls `record_replay` to produce channel snapshots, signals, confirmed extrema, and extremum candidates.
- **FR-002**: The system MUST run for each configured timeframe ([[REQ-WP-073]]), not only the ingested one.
- **FR-003**: A second pass over unchanged bars MUST write **zero** new rows to `channel_snapshots`, `signals`, `confirmed_extrema`, `extremum_candidates` — proven by counting rows before and after.
- **FR-004**: A timeframe with no bars MUST be skipped with a log message, not an error.
- **FR-005**: Channel snapshots MUST be written once and never rewritten — Constitution III and §29.6. A re-fit of an already-recorded moment MUST NOT replace it.
- **FR-006**: One timeframe failing MUST NOT stop the pass; the failure is logged with venue/symbol/timeframe, and remaining timeframes are processed.
- **FR-007**: A signal MUST reach the table in its final state only, never one row per bar — the property [[REQ-PIPE-001]] established, re-checked here because a loop invokes it far more often than a fixture does.

### Key Entities

- **ChannelSnapshot**: Immutable record of a fitted channel at a specific `(venue, symbol, timeframe, open_time_ns)`, with upper/lower/center lines and metadata.
- **Signal**: A trading signal in its final confirmed state, never intermediate states.
- **ConfirmedExtremum**: A confirmed peak/trough with timestamp, price, and type.
- **ExtremumCandidate**: A potential extremum still being confirmed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After one pass, `GET /api/v1/channels` answers for a `(venue, symbol, timeframe)` that has bars, where before it answered with nothing.
- **SC-002**: A pass covers every configured timeframe, not only the ingested one — measured by channel snapshots present for each timeframe that has bars.
- **SC-003**: A second pass over unchanged bars writes zero new rows across `channel_snapshots`, `signals`, confirmed extrema and extremum candidates, measured by row counts taken before and after.
- **SC-004**: One timeframe failing does not end the pass: the failure names its venue, symbol and timeframe, and every remaining timeframe completes.
- **SC-005**: For every signal the pass records, the table holds exactly one row, carrying the signal's final state — never one row per bar of its life.

## Assumptions

- The resampler ([[REQ-WP-073]]) produces bars for all configured timeframes before this feature's pass runs.
- The `record_replay` function in `channelflow.pipeline.replay` is correct and tested; this feature only wires it into a scheduled loop.
- The `bars` table has data for the configured timeframes before the first pass runs.
- The deployment runs with at least one configured timeframe (validated at startup).
- Timeframe configuration comes from `CHANNELFLOW_TIMEFRAMES` (set by [[REQ-WP-073]]).
- The `record_replay` function's watermark/idempotency logic is correct; this feature only schedules its execution.
