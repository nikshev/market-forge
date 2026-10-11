---
traces: [REQ-WP-094]
status: draft
---

# Feature Specification: The liquidations pane is fed by each venue's liquidation stream

**Feature Branch**: `146-liquidations-collector`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-094]] -- owner's direction 2026-10-11; PRD §10.5, §16.4, §27.3. Principle I, II, [[ADR-070]]; shares the collector of [[REQ-WP-093]] (spec 145).

## Context

### Facts measured on 2026-10-11, not assumed

1. **There is no liquidation parser on any venue**, not an unwired one: `connectors/*/normalize.py` handle trades, books and derivatives state only. No `LiquidationEvent` is stored anywhere. The pure functions exist (`derivatives/liquidations.py`: `window`, `intensity`, `clusters`, `time_since_spike`) and `liquidation_imbalance_5m` is registered.
2. **Three public, keyless streams connect from this host**: Binance USD-M `<symbol>@forceOrder`, Bybit `allLiquidation.<symbol>` on the linear socket (subscription acknowledged), OKX `liquidation-orders` for SWAP (subscription acknowledged). Binance's stream sent no frame in a 12-second probe, which is what a sparse event stream looks like and is why this spec treats silence as normal and a dead connection as something else.
3. **A liquidation order is the opposite side of the position closed**: a forced SELL closes a long. Reading the order's side as the position's flips the sign of every number downstream.
4. **`LiquidationWindow.imbalance` is `None` for an empty window**, deliberately: zero liquidations and no data must not both read as balanced.
5. The series the deployment has: Binance BTC/ETH/SOL (spot markets, with the venue's perpetual as the derivatives source), Bybit BTC and OKX BTC (perpetuals).

### What this is not

Long/short ratios, liquidation heat maps by price (§16.4's "clusters by price" stays a library function with no pane), and any pane or API change.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The pane shows what was liquidated (Priority: P1)

Someone opens a chart whose venue emitted liquidations in the loaded range, selects Liquidations (5m), and sees the net imbalance over time.

**Why this priority**: the owner's request.

**Independent Test**: after the collector has run and the worker has finished a pass, the features endpoint carries `liquidation_imbalance_5m` for the bars whose trailing five minutes contained a liquidation, and the pane is enabled.

**Acceptance Scenarios**:

1. **Given** a fixture of long- and short-side events, **When** the worker computes a bar's features, **Then** the long and short USD over the trailing 5 minutes and their imbalance equal the library's `window()`.
2. **Given** a window with no events, **When** the features are computed, **Then** no imbalance row is written, and the USD sums (which are true zeros) are written only if the collector covered the window (User Story 3).

---

### User Story 2 - The side of a liquidation is the position's, not the order's (Priority: P1)

**Why this priority**: a sign error here is invisible in a chart and wrong in every conclusion.

**Independent Test**: one recorded frame per venue, parsed, with the expected position side asserted explicitly in the test.

**Acceptance Scenarios**:

1. **Given** a Binance `forceOrder` frame with side SELL, **When** parsed, **Then** the event is `long_liquidated`.
2. **Given** a Bybit `allLiquidation` frame whose side is the liquidated position's, **When** parsed, **Then** the mapping follows the venue's documented meaning (stated per venue in the module, with the frame that proves it).
3. **Given** an OKX `liquidation-orders` frame, **When** parsed, **Then** the event's side is derived from `posSide`/`side` per OKX's documentation, and an ambiguous combination yields `unknown`, never a guess.

---

### User Story 3 - Quiet is a reading only where the collector was listening (Priority: P1)

**Why this priority**: otherwise a collector outage draws an hour of "no liquidations".

**Independent Test**: a window inside a gap in the collector's heartbeat produces no row; the same window with a heartbeat and no events produces zero USD and no imbalance.

**Acceptance Scenarios**:

1. **Given** no heartbeat state in the window, **When** the worker runs, **Then** no liquidation feature is written for bars in it.
2. **Given** heartbeats throughout and no events, **When** the worker runs, **Then** long and short USD are 0 and the imbalance is absent.

---

### User Story 4 - A silent socket is told from a quiet market (Priority: P2)

**Independent Test**: a stream that sends no frame and no ping response for the stated window is closed and reconnected, and a duplicate event after reconnect is not stored twice.

**Acceptance Scenarios**:

1. **Given** a connection that stops answering pings, **When** the window passes, **Then** the collector reconnects and says so in its log and metrics.
2. **Given** the same event delivered twice, **When** stored, **Then** it appears once.

### Edge Cases

- A symbol with no liquidation stream on a venue (OKX `liquidation-orders` is per instrument type, not per symbol): filtered to the configured symbols in the collector, and the filter is tested.
- A frame with a zero or negative price/quantity: refused with a reason, not stored (the event type's own constraints).
- `notional_usd` for a venue that reports contracts, not base units: converted by the venue's documented contract size, stated per instrument; an unknown contract size refuses the event rather than guessing.
- A burst (a cascade): the buffered sink batches; a single commit never contains more than a stated number of rows.
- A reconnect storm: backoff, capped, and the failure counter visible.
- The Binance spot series' liquidations come from its perpetual (spec 145 FR-012), declared in the same configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The collector subscribes to each venue's public liquidation stream for the configured perpetual symbols and parses each frame into a §10.5 `LiquidationEvent`.
- **FR-002**: The event's `side` is the closed position's side, derived per venue and pinned by a recorded frame; an unmappable frame is `unknown`.
- **FR-003**: `notional_usd` is price times quantity in base units, converted from contracts where the venue reports contracts, with the contract size stated per instrument.
- **FR-004**: Events are stored append-only in a `liquidations` table: event time (venue's) and ingest time apart, decimals for price, quantity and notional, identity (venue, symbol, event time, price, quantity, side) enforced against duplicates after a reconnect.
- **FR-005**: A silent connection is detected by a stated window and reconnected with capped backoff; the failure and reconnect counts are metrics.
- **FR-006**: The worker, per series and timeframe, writes `liquidation_long_usd_5m`, `liquidation_short_usd_5m`, `liquidation_imbalance_5m`, `liquidation_intensity_5m` and `time_since_liquidation_spike` at each bar's close from events with event time at or before it.
- **FR-007**: A window is written only where the collector's heartbeat covers it; the imbalance of an empty window is absent; no feature is ever written as zero for "unknown".
- **FR-008**: The intensity uses the bar's own traded USD volume; a bar with none has no intensity.
- **FR-009**: Value at a bar's close is unchanged by events appended later (a test), and the worker is the only writer of `feature_snapshots`.
- **FR-010**: The six trade features, and the features of specs 145 and 147, keep their values and counts.
- **FR-011**: Every new file carries a requirement trace.

### Key Entities

- **LiquidationEvent** (§10.5) as stored, plus ingest time and source tag.
- **Collector heartbeat**: the derivatives states of spec 145, polled every minute, read as proof that the collector was up.
- **Liquidation feature row**: (at_ns = bar close, venue, symbol, timeframe, feature name, value).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For one recorded frame per venue the parsed event matches the hand-computed side, price, quantity and notional (3 of 3).
- **SC-002**: A bar's liquidation features are identical before and after appending later events across the fixture (zero differences).
- **SC-003**: With the collector's heartbeat absent for a window, zero bars in it carry a liquidation feature.
- **SC-004**: On the running stack after 24 hours the liquidation pane is enabled for every series whose venue stored at least one event in the loaded range, and reads "no data" for any other, each with the recorded query naming which.
- **SC-005**: A delivered-twice event is stored once (zero duplicates in the fixture).
- **SC-006**: The collectors' combined CPU stays under the figure of spec 145 (5% of one core) with this stream added.

## Assumptions

- The public streams stay keyless and within their documented subscription limits; one connection per venue carries all configured symbols.
- Bybit's `allLiquidation` frame states the liquidated position's side (to be confirmed against its documentation and a recorded frame in the plan); if it does not, the parser derives it and the test says how.
- Event volume for the configured symbols is low enough that one table commit per flush interval is sufficient.
