---
traces: [REQ-WP-090]
status: draft
---

# Feature Specification: The chart follows the market without a reload

**Feature Branch**: `139-live-refresh`

**Created**: 2026-10-05

**Status**: Draft

**Input**: [[REQ-WP-090]] — PRD §27, §28.7; the owner's direction of 2026-10-04.

## Context

The owner opened an ETHUSDT chart and it sat still: a new candle appears only after a manual reload.

### Facts read from the code, which decide the design

- `App.tsx` loads its data **once** (on mount, and when the timeframe or the channel mode changes): `fetchTimeframes` once,
  then `fetchBars` (limit 500), `fetchChannel`, `fetchFeatureSeries`, `fetchExtrema` (and `fetchDexDepth` when the link names
  a pool, `fetchVolumeProfile` when the `volume_profile` layer is on). There is no timer and no WebSocket client in
  `apps/web`, so nothing re-reads after the first answers arrive.
- `Chart.tsx` resets the visible range on **every** data change (`fitContent`, or `setVisibleLogicalRange` for a deep link's
  instant or the channel window). Re-reading the data with this effect unchanged would yank the reader's pan and zoom back
  on every refresh: the range reset is the thing a refresh must not repeat.
- The load is guarded by a `loadId`: a response whose load was superseded is discarded, so two fast clicks end on the
  second. A refresh is a third, fourth, fifth load through the same guard; the rule it needs on top is that a tick never
  starts while the previous load is still in flight.
- `LoadState.tsx` already names the vocabulary a refresh failure must use: `empty` is a fact about the market, `failed`
  (role `alert`) a fact about us, `disconnected` a feed that stopped. A failed refresh must keep the old picture and say
  so in these words, never blank the chart or show a failure as an empty market (FR-016, REQ-WP-009).
- The reader's state lives beside the data, not in it: `timeframe` and `mode` (written to the address), `pane` (kept by
  `chooseSelection`, which already prefers the current pane when it still has data), `showCandidates` (off on every load,
  never part of the link). A refresh must not touch any of them; the defect it removes is a refresh that resets them.
- The pinned chart is `link.atNs !== null`: `atNsForDepth` and the profile fetch already branch on it, and the channel and
  extrema are asked as of that instant. A pinned chart is a historical view; moving it would answer a question nobody asked.
- The latency floor is the producers', not the page's: higher timeframes are resampled every 5 minutes and channels and
  extrema are produced by the worker every 5 minutes. The page cannot show a bar the API does not yet serve; the interval
  only decides how soon after the API has it the page asks again.

### What this is not

Not the push path. The requirement's stage 2 (worker events through the API's `/ws/market` hub to the page, the interval
kept as a fallback) crosses a process boundary and is a design decision of its own; the requirement itself says it may be
split into its own requirement when specified. This spec is stage 1: refresh by reading again. No WebSocket client, no hub
wiring, no worker changes here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A finished bar appears without a reload (Priority: P1)

**Why this priority**: this is the requirement: the page follows the market.

**Independent Test**: with a clock and a replaced API, open a live chart, finalise a bar after load, advance the clock past
the interval, and read the chart's bars.

**Acceptance Scenarios**:

1. **Given** a live (unpinned) chart, **When** the API gains a finished bar and the refresh interval passes, **Then** the
   chart shows the new bar, its channel and its extrema without any reload or click.
2. **Given** the same chart, **When** no new bar was finalised, **Then** the refresh re-reads and the picture is unchanged
   (no flicker, no reset, no duplicate request while the previous one is in flight).
3. **Given** the `volume_profile` layer on, **When** a refresh runs, **Then** the profile is re-read for the same window
   (as of the newest closed block on a live chart, as of the link's instant on a pinned one — which never refreshes).

---

### User Story 2 - A refresh keeps what the reader chose (Priority: P1)

**Why this priority**: a refresh that resets the timeframe, the pane or the zoom is a reload wearing a timer.

**Independent Test**: change each piece of state, run a refresh, read each back.

**Acceptance Scenarios**:

1. **Given** a changed timeframe, channel mode, lower pane, candidate switch and a panned/zoomed visible range, **When** a
   refresh runs, **Then** all five are unchanged afterwards.
2. **Given** the first load, **When** it answers, **Then** the visible range is set exactly as today (deep link's instant
   centred, else the channel window, else everything fitted); **given** a refresh, **When** it answers, **Then** no code
   resets the range — the library keeps the reader's range, and a new bar at the edge appears without moving it.
3. **Given** a pane that still has data after the refresh, **Then** it stays selected; **given** one that lost it, **Then**
   the existing `chooseSelection` rule decides, as today.

---

### User Story 3 - A pinned chart, a hidden tab and a failed refresh (Priority: P1)

**Why this priority**: each is a way a well-meaning refresh lies: moving history, polling nobody sees, or blanking the
chart.

**Independent Test**: each with a replaced API and a clock or a visibility event.

**Acceptance Scenarios**:

1. **Given** a chart opened with `at` (a historical view), **When** the interval passes any number of times, **Then** no
   refresh request is issued.
2. **Given** a live chart whose tab becomes hidden, **When** the interval passes, **Then** no request is issued; **when** the
   tab becomes visible again, **Then** exactly one refresh runs.
3. **Given** a live chart, **When** a refresh fails, **Then** the previous bars, channel, extrema and pane stay drawn, the
   failure is stated (the `failed` vocabulary, role `alert`, never as an empty market), and **when** the next refresh
   succeeds, **Then** the notice clears and the new data is drawn.
4. **Given** a refresh in flight, **When** the interval fires again, **Then** the tick is skipped: at most one load runs at
   a time, and the superseded-response guard (`loadId`) still decides every answer.

---

### User Story 4 - Looked at, on the running stack (Priority: P2)

1. **Then** with the page open on a live chart, a bar finalised after load appears within the configured interval without
   a reload, on the running stack; the interval is the configured value (default 60 s).

### Edge Cases

- A refused timeframe or a failed offered set: no timer starts, exactly as no series request goes out today.
- An initial load that failed or is empty: the refresh still runs on a live chart (empty is a state that a new bar leaves);
  a failed first load states the failure as today, and a later success draws.
- The forming (unfinalised) last bar changes between refreshes: drawn as today, never treated as history rewritten.
- A refresh that answers out of order with a timeframe or mode change: the `loadId` guard discards it, as today.
- Unmount: the timer and the visibility listener are removed; no request after the page is gone.
- The interval is zero or unparseable: treated as absent (no refresh), never as a tight loop.
- Nothing here changes a past channel snapshot or a confirmed extremum (Principle III): a refresh only draws what the API
  newly serves.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: On a live chart (`at` absent) the page MUST re-run the same series load it ran on open — bars, channel,
  feature series, extrema (and the volume profile when the layer is on, DEX depth when the link names a pool) — on a
  configured interval, and draw the answers without a reload.
- **FR-002**: The interval MUST be configuration (Principle X), read from `VITE_CHART_REFRESH_MS`, default 60 000 ms;
  a missing, zero, negative or unparseable value MUST disable the refresh rather than poll tightly.
- **FR-003**: A pinned chart (`at` present) MUST issue no refresh requests.
- **FR-004**: A hidden tab (`document.hidden`) MUST issue no refresh requests; when the tab becomes visible again the page
  MUST run exactly one refresh.
- **FR-005**: A refresh MUST NOT start while the previous load is in flight; a tick that finds one running MUST be skipped.
- **FR-006**: A failed refresh MUST leave the previous data drawn, MUST state the failure in the `failed` vocabulary
  (role `alert`, with the detail, never as an empty chart), and MUST clear the notice when a later refresh succeeds.
- **FR-007**: A refresh MUST preserve the selected timeframe, channel mode, lower pane, candidate switch and the visible
  range the reader set; only the initial load (and a timeframe or mode change) may set the range.
- **FR-008**: The refresh MUST NOT alter history: channel snapshots and confirmed extrema already drawn are never rewritten
  by a refresh, only added to (Principle III).
- **FR-009**: No WebSocket client and no hub/worker wiring in this spec (stage 2 is explicitly out; the interval here is
  the mechanism, not the fallback).

### Key Entities

- **Refresh tick**: one re-run of the page's series load on the interval, skipped when pinned, hidden, unconfigured, or
  already in flight.
- **Reader state**: timeframe, channel mode, lower pane, candidate switch, visible range — owned by the reader, untouched
  by a tick.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the page open on a live chart, a bar finalised after load is drawn within one configured interval
  (default 60 s) without a reload — shown by a clock-and-replaced-API test and on the running stack.
- **SC-002**: A test that changes the timeframe, mode, pane, candidate switch and visible range, refreshes, and finds all
  five unchanged.
- **SC-003**: A pinned chart issues zero refresh requests over any number of intervals; a hidden tab issues zero while
  hidden and exactly one on becoming visible; overlapping ticks never run two loads at once.
- **SC-004**: A failed refresh leaves the previous data drawn with a stated failure, and the next successful refresh
  recovers it.
- **SC-005**: The existing web and Python tests pass with only the edits the outcome note lists.

## Assumptions

- The default 60 s interval is the requirement's own; the producers' 5-minute passes set the freshness floor, so a
  shorter interval shows nothing newer on most timeframes.
- `VITE_CHART_REFRESH_MS` is a build-time value (Vite `import.meta.env`), like the existing `VITE_API_BASE`; changing it
  rebuilds the web image.
- The volume profile refreshes on the same tick; its own window selector is reader state and is preserved like the rest.
- The push path (stage 2) will arrive as its own requirement and spec; this spec must not make it harder (the tick stays
  as the fallback).
