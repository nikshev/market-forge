---
traces: [REQ-WP-087]
status: draft
---

# Feature Specification: Extremum detector and channel gap policy

**Feature Branch**: `141-detector-gap-policy`

**Created**: 2026-10-06

**Status**: Draft

**Input**: [[REQ-WP-087]] — PRD §13A, §13.1, §32; stateful-feature gap rule of §15/§18 acceptance; owner's direction 2026-10-04.

## Context

Both the channel fit and the extremum detector count **bars**, not time. Neither knows a bar is missing.

### Facts read from the code

- **Channel fit** (`channels/window.py`): takes "the most recent `lookback` finalized bars" (`lookback` = 60 default). Over a hole, the 60 bars cover as long as the hole makes them — i.e., the window straddles the gap.
- **Directional-change detector** (`extrema/detector.py`): advances one bar at a time; measures confirmation in bars (`confirmation_lag_bars`). A jump in price across a hole looks like one step.
- **Measured on ETHUSDT 1h** (2026-10-04): hole of 148 hourly bars (26.09 06:00 → 02.10 11:00). A LOW turning at 25.09 22:00 recorded as known at 02.10 12:00 with `confirmation_lag_bars` of 10 (a week later); the channel on 02.10 is fitted to a window that, counted in time, reaches back more than a week before its first bar.

### PRD rules that apply

- §13.1: a snapshot never carries hindsight; the model guards its own invariant.
- §15/§18 acceptance: "forced sequence gap disables book features" / "forced log gap disables stateful features until repaired".
- §32: missing bars is a health metric (`GOOD` / `DEGRADED` / `STALE`).
- Principle I: no look-ahead — test appends later bars and checks earlier record unchanged.
- Principle X: threshold for "a hole" is configuration, not a constant.

### The decision needed

Three policies, with recommendation:

1. **Bridge** (today): treat bars as consecutive. Simple, wrong across long holes.
2. **Restart at the gap** (recommended): hole >1 step ends model state. Detector forgets direction/running extreme; channel fits only to bars after hole, absent until `lookback` contiguous bars exist (or flagged short). Same shape as OFI rule.
3. **Fill** (carry-forward/interpolate): rejected — fabricates bars (immutability, no-hindsight).

**Owner confirmation needed** on policy 2 (restart at gap). This spec assumes policy 2.

### What this is not

- Not filling/interpolating holes.
- Not bridging (today's behavior).
- Not a general gap detector for all models — only channel and extremum detector.
- Not the gap marking on the chart (that's [[REQ-WP-086]]).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extremum detector restarts at gap (Priority: P1)

**Why this priority**: Core model behavior; prevents false confirmations across holes.

**Independent Test**: Feed detector bars with a hole; verify state reset and no straddling confirmation.

**Acceptance Scenarios**:

1. **Given** bars with a hole (>1 step), **When** detector processes bars before the hole, **Then** it tracks direction/running extreme normally.
2. **Given** the hole, **When** detector processes the first bar after the hole, **Then** it starts a fresh observation (direction=UNKNOWN, running_extreme=first bar, no open candidate).
3. **Given** a turn before the hole and a confirming bar after it, **Then** no confirmation is emitted (turn and confirm on opposite sides of hole).
4. **Given** a turn after the hole with enough confirming bars, **Then** confirmation is emitted with lag measured only from bars after the hole.
5. **Given** the same bars with later bars appended, **Then** the record at the earlier instant is unchanged (no look-ahead, Principle I).

---

### User Story 2 - Channel fits only to bars after gap (Priority: P1)

**Why this priority**: Channel must not straddle hole; snapshot absent/short until `lookback` contiguous bars.

**Independent Test**: Feed channel bars with a hole; verify fit window and snapshot behavior.

**Acceptance Scenarios**:

1. **Given** bars with a hole, **When** channel fits at a bar before the hole, **Then** it uses `lookback` bars before the hole (normal).
2. **Given** the hole, **When** channel fits at the first bar after the hole, **Then** it fits only to that bar (window=1) — no bars from before the hole included.
3. **Given** bars after the hole, **When** fewer than `lookback` contiguous bars exist, **Then** snapshot is absent or carries `window_short=true` flag.
4. **Given** `lookback` contiguous bars after the hole, **Then** snapshot is normal (window=`lookback`).
5. **Given** the same bars with later bars appended, **Then** the snapshot at an earlier instant is unchanged (Principle I).

---

### User Story 3 - Configuration for hole threshold (Priority: P1)

**Why this priority**: Principle X — threshold is config, not constant.

**Independent Test**: Vary threshold; verify behavior at boundary.

**Acceptance Scenarios**:

1. **Given** threshold = 1 (default), **When** 1 bar missing, **Then** treated as contiguous (no restart); **when** 2+ bars missing, **Then** restart.
2. **Given** threshold = 0, **When** any bar missing, **Then** restart.
3. **Given** threshold >1, **When** hole size ≤ threshold, **Then** contiguous; else restart.

---

### User Story 4 - Confirmation lag in time and bars (Priority: P2)

**Why this priority**: §32 — lag in bars only meaningful on contiguous series.

**Independent Test**: Verify confirmed extremum carries both lag measures.

**Acceptance Scenarios**:

1. **Given** a confirmed extremum on contiguous bars, **Then** it has `confirmation_lag_bars` and `confirmation_lag_ns` (time difference between turn and confirming bar).
2. **Given** a turn before hole and confirm after (not emitted per US1), **Then** no record exists with straddling lag.
3. **Given** the live ETHUSDT 1h series (148-bar hole), **Then** records before and after hole are separate runs; zero records straddle the hole.

---

### User Story 5 - Live validation (Priority: P2)

1. **Then** on ETHUSDT 1h (148-bar hole), detector and channel records before/after hole are separate; count of straddling records is zero.

### Edge Cases

- Hole exactly at threshold boundary (1 vs 2 missing bars).
- Hole at very start/end of loaded range (no bars on one side).
- Multiple holes in one series.
- Hole within `lookback` window of channel.
- Detector state exactly at hole boundary (turn on last bar before hole).
- Confirmation lag measured in time when bars have variable duration (always 1h here, but principle holds).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Extremum detector MUST detect a hole (> `gap_threshold` missing bars) from the bars it is given; MUST NOT rely on caller.
- **FR-002**: On a hole, detector state (direction, running extreme, open candidate) MUST reset; first bar after hole starts fresh observation.
- **FR-003**: NO confirmation MUST be emitted whose turn is before a hole and whose confirming bar is after it.
- **FR-004**: Channel fit MUST use only contiguous bars after a hole; MUST NOT include bars from before the hole.
- **FR-005**: Channel snapshot MUST be absent (or `window_short=true`) until `lookback` contiguous bars exist after hole.
- **FR-006**: `gap_threshold` MUST be configuration (default 1); threshold=0 means any gap restarts; threshold>1 means hole size > threshold restarts.
- **FR-007**: Confirmed extremum MUST carry `confirmation_lag_ns` (time) in addition to `confirmation_lag_bars`.
- **FR-008**: NO record (channel snapshot or extremum) MUST straddle a hole — i.e., be based on bars from both sides.

### Key Entities

- **Gap**: detected from bar series — `next.open_time_ns - prev.close_time_ns > timeframe_ns * (gap_threshold + 1)`
- **DetectorState**: `direction`, `running_extreme`, `open_candidate`, `last_bar_close_ns`
- **ChannelSnapshot**: `window_bars`, `window_short`, `bars_after_gap`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Detector on fixture with hole emits no confirmation straddling it; fresh observation after hole.
- **SC-002**: Channel on fixture with hole fits only to bars after hole; snapshot absent until `lookback` contiguous bars.
- **SC-003**: Threshold=1 (default) treats 1 missing bar as contiguous, 2+ as hole; threshold=0 treats any gap as hole.
- **SC-004**: Confirmed extremum has `confirmation_lag_ns`; no straddling records on ETHUSDT 1h live series.
- **SC-005**: Existing tests pass; traceability clean.

## Assumptions

- Policy 2 (restart at gap) confirmed by owner; if policy changes, spec updates.
- `lookback` for channel is already config (60 default).
- Bar timeframe is known to both models (passed as parameter).
- The gap detection uses bar timestamps, not time — a "hole of N bars" means N missing bar slots.