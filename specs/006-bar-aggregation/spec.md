---
traces: [REQ-WP-005]
status: draft
---

# Feature Specification: Bar aggregation

**Feature Branch**: `wp-005-bar-aggregation`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-005 — event-time windows; late-event policy; finalized bar callback; trade-side aggregates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Aggregate trades into bars by event time (Priority: P1)

Normalized trades become OHLCV bars on fixed event-time windows, carrying the
fields PRD §12 lists — including the aggressive buy and sell volumes that make
order-flow analysis possible later.

**Why this priority**: Bars are what the channel engine, the chart, the backtest
and the order-flow features all consume. Nothing in Phase 1 proceeds without
them.

**Independent Test**: Feed a known sequence of trades and compare the resulting
bar field by field. Pure, no services.

**Acceptance Scenarios**:

1. **Given** trades within one window, **When** the bar is built, **Then** open, high, low and close come from the first, highest, lowest and last trade by event time.
2. **Given** trades on both sides, **When** the bar is built, **Then** aggressive buy volume and aggressive sell volume are separated and their difference is the delta volume.
3. **Given** any bar, **When** it is built, **Then** its VWAP is the notional divided by the base volume, computed exactly rather than through a float.
4. **Given** trades arriving out of order within a window, **When** the bar is built, **Then** open and close still follow event time, not arrival order.

---

### User Story 2 - Never amend a bar that has closed (Priority: P1)

A trade arriving after its window has finalized is discarded and counted. The
bar that was already published stays exactly as published.

**Why this priority**: Equal to US1 and arguably above it. PRD §0.5 forbids
rewriting finalized snapshots and §0.3 forbids a value computed at time `t`
changing afterwards. A bar that quietly amends itself is repainting — the single
failure this project exists to prevent.

**Independent Test**: Finalize a bar, then feed a trade belonging to it; the bar
is unchanged and a counter increased.

**Acceptance Scenarios**:

1. **Given** a finalized bar, **When** a trade belonging to its window arrives, **Then** the bar is unchanged and the late-trade counter increases.
2. **Given** an open bar whose window has ended but whose grace period has not, **When** a trade belonging to it arrives, **Then** it is accumulated normally.
3. **Given** a bar, **When** it is finalized, **Then** it is marked final and no later input can change that.
4. **Given** the same trades fed in a different order, **When** all bars finalize, **Then** the resulting bars are identical.

---

### User Story 3 - Learn when a bar is ready (Priority: P2)

A consumer is told the moment a bar finalizes, so the channel engine can compute
on closed bars without polling for them.

**Why this priority**: Required by REQ-WP-005 and needed by every consumer, but
it is delivery rather than correctness.

**Independent Test**: Register a callback, feed trades across a window boundary,
observe exactly one call with the finalized bar.

**Acceptance Scenarios**:

1. **Given** a registered callback, **When** a bar finalizes, **Then** it is called once with that bar.
2. **Given** a bar that has not finalized, **When** trades accumulate, **Then** the callback is not called.
3. **Given** several windows crossed at once by a large time jump, **When** the watermark advances, **Then** every intervening bar finalizes in event-time order.

---

### Edge Cases

- What happens when no trades arrive for a long time? The last bar stays open. With no events there is no evidence its window has passed, and inventing time would make bars depend on our clock.
- What happens when a single trade jumps the watermark past several windows? Every skipped window finalizes, in order. Windows with no trades produce no bar rather than an empty one.
- What happens to a trade exactly on a window boundary? It belongs to the window that opens at that instant, not the one that closes.
- What happens when the same trade is delivered twice? It is counted twice unless the caller deduplicates first — the builder aggregates what it is given, and PRD §11.2's identity exists for the caller to use.
- What happens when a bar has volume but the price never moves? High, low, open and close coincide, which is a valid bar rather than a degenerate one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The builder MUST aggregate trades into bars on fixed event-time windows of a configurable timeframe.
- **FR-002**: A bar MUST carry every field PRD §12 lists: open, high, low, close, base volume, quote volume, trade count, aggressive buy volume, aggressive sell volume, delta volume, VWAP, high and low timestamps, first and last trade identifiers, and whether it is final.
- **FR-003**: Open and close MUST be determined by event time, not by arrival order.
- **FR-004**: Aggressive buy and sell volumes MUST be separated using the trade's aggressor side, and delta volume MUST be their difference.
- **FR-005**: Monetary aggregates MUST be computed with exact decimals, never through floating point.
- **FR-006**: A bar MUST finalize when the watermark — the highest observed event time — passes its window end plus a configurable grace period.
- **FR-007**: The watermark MUST derive only from event time. Wall-clock time MUST NOT influence bar boundaries.
- **FR-008**: A trade whose window has already finalized MUST be discarded, and a late-trade counter MUST increase.
- **FR-009**: A finalized bar MUST NOT be modified by any later input.
- **FR-010**: A trade arriving after its window ends but within the grace period MUST be accumulated.
- **FR-011**: The builder MUST invoke a callback once per bar at finalization, with the finalized bar.
- **FR-012**: When the watermark crosses several windows at once, every intervening window with trades MUST finalize in event-time order.
- **FR-013**: Feeding the same trades in a different order MUST produce identical finalized bars.
- **FR-014**: The timeframe and the grace period MUST be configuration, not constants in code.

### Key Entities

- **Bar**: one event-time window's aggregate of trades, and whether it can be trusted as complete.
- **Bar builder**: holds at most one open window per timeframe, decides when it closes, and refuses to revisit it afterwards.
- **Watermark**: the highest event time seen. The only thing that advances time in this system.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A known trade sequence produces a bar whose fourteen fields all match expected values.
- **SC-002**: Feeding a trade belonging to a finalized bar leaves the bar byte-identical and raises the late counter by one.
- **SC-003**: The same trades in shuffled order produce identical finalized bars.
- **SC-004**: A watermark jump across three windows finalizes them in event-time order.
- **SC-005**: A trade after the window end but inside the grace period is included in the bar.
- **SC-006**: No wall-clock call appears anywhere in the builder — verifiable by inspection and by the absence of a clock argument.
- **SC-007**: VWAP computed from a price with more digits than a double holds is exact.

## Assumptions

- Bars are built from normalized trades, not from exchange klines. PRD §12 prefers this, and it is what makes the aggressive-side split possible at all.
- The builder handles one symbol and one timeframe per instance. Running several is the caller's composition, which keeps the state machine small enough to reason about.
- Deduplication is the caller's responsibility. The builder aggregates what it is given; PRD §11.2 defines the identity to deduplicate on, and doing it here would duplicate that logic in every consumer.
- The grace period defaults to five seconds. This is a starting value rather than a measured one — ADR-005 records that it needs checking against real venue behaviour.
- No persistence. Bars are produced and handed to a callback; PRD §29.4's storage is a later concern.
