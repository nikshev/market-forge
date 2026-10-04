---
traces: [REQ-WP-088]
status: draft
---

# Feature Specification: CVD and the trade-imbalance features, from the aggressor volumes the bars already carry

**Feature Branch**: `135-trade-flow-features`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-088]] — PRD §15.4, §27.3, §29.5; the owner's direction of 2026-10-04.

## Context

`features/flow.py` ([[REQ-WP-011]]) holds the §15.4 arithmetic over trades; nothing runs it, the features table is
empty and the CVD pane reads "no data" ([[REQ-WP-084]]). The first version of this specification planned a new
trade-level producer in the ingest. **Reading the bars table showed that is not needed.**

### Facts read from the code, which decide the design

- **Every bar already stores the split by aggressor side.** `Bar` and the bars table carry `aggressive_buy_base`,
  `aggressive_sell_base`, `delta_base` (buy minus sell), `trade_count`, `volume_base`, `volume_quote`,
  `first_trade_id` and `last_trade_id`. The bar builder fills them from the trades it sees; `resample.fold` sums
  them (and takes the first and last trade ids) for every higher timeframe, **only from complete windows**. The
  API's `BarOut` simply does not expose them. So the data exists for every series since its ingest started, at
  every timeframe, with no change to ingest or to resample.
- The worker pass (`channel_main.run_series`) already reads every bar of a `(venue, symbol, timeframe)` and writes
  channels, signals and extrema with a read-before-write watermark. A flow step fits there, deterministically,
  with no new process and no coupling to the socket process.
- The split is stored in **base units** (the asset), while PRD §15.4 and `flow.py` define delta in **notional**
  (quote currency). The bar carries the quote *total* only. Recomputing notional per side would need the
  quote split stored in the bar (a schema change to the central table, forward-only). That is not done here; the
  deviation is recorded in [[ADR-068]], with the way back, and the new features are named for what they are
  (`*_base`) so nothing claims to be the notional the registry's `cvd` describes.
- Continuity can be read from the bars themselves. A missing bar is visible as a gap in `open_time_ns`. For venues
  whose trade ids are sequential per symbol (Binance `aggTrade`), a missed trade is visible as a jump between
  one bar's `last_trade_id` and the next bar's `first_trade_id`, or inside a bar as `last − first + 1 != trade_count`.
  Bybit's ids are not numeric and OKX's are not sequential (measured, SC-005): for them only a missing bar is detectable (a stated limit).

### CVD is a running sum, and a running sum is wrong forever after one missed trade

`CVD_t = CVD_{t-1} + delta_t`. A missing bar or a missed trade makes every later value off by an unknown amount.
So the sum is kept within a **run**: a stretch of consecutive bars with no break. A break ends the run; the next
bar starts a new one at zero. A window spanning two runs is not comparable. The chart's line is broken where the
run changes. The same lesson as [[REQ-WP-087]]'s gaps, one level down.

### What this is not

Not the book features (OFI, depth imbalance), not derivatives, not the price-bin volume profile ([[REQ-WP-089]],
which needs trades by price and is not in a bar), not CVD-price divergence (ADR-013), not the notional split.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Flow features from bars (Priority: P1)

**Independent Test**: give the function bars with known aggressor volumes and read the rows.

**Acceptance Scenarios**:

1. **Given** bars with known `aggressive_buy_base` and `aggressive_sell_base`, **Then** per bar, at its close:
   `delta_base` is buy minus sell, `cvd_base` the running sum within the run, `normalized_delta_base` the delta
   over `volume_base` (**absent**, not zero, when nothing traded), `cvd_base_slope` the delta over the bar's
   seconds, and `cvd_base_acceleration` the change of slope per bar (**absent** in a run's first bar).
2. **Given** bars later than a bar, **Then** that bar's rows are unchanged by them (no look-ahead).
3. **Given** a forming bar (`is_final` false), **Then** it produces no row.
4. **Given** the same bars in any order, **Then** the same rows (the function sorts by time; no arrival order matters).

---

### User Story 2 - A break is recorded, not hidden (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a missing bar (a gap in `open_time_ns` larger than the timeframe), **Then** the run ends and the next
   bar starts a new run at zero with a higher `cvd_run`.
2. **Given** consecutive Binance bars where the next `first_trade_id` is not the previous `last_trade_id + 1`,
   **Then** the run ends between them.
3. **Given** a Binance bar whose `last − first + 1` differs from its `trade_count`, **Then** the bar is incomplete:
   it produces no flow row and a run ends before it and starts after it.
4. **Given** a venue whose ids are not sequential, **Then** only a missing bar breaks the run (the limit is
   documented, not hidden).

---

### User Story 3 - Written once, every timeframe, by the worker (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a worker pass, **Then** flow rows are written for every `(venue, symbol, timeframe)` it processes, from
   the same bars it reads for the channels.
2. **Given** a second pass over bars already processed, **Then** nothing is written twice (it reads the latest row
   on record and writes only after it).
3. **Given** a 15m bar, **Then** its flow comes from its own stored fields (the sums `resample.fold` already
   made over a complete window); no second source of 15m flow exists.
4. **Given** the same bars through two passes (live and a replay), **Then** identical rows: it is one pure function.

---

### User Story 4 - The CVD pane draws it, broken at a run change (Priority: P1)

**Acceptance Scenarios**:

1. **Given** flow rows for the chart's market and timeframe, **Then** the CVD (base) pane is live and draws the line.
2. **Given** `cvd_run` changes between two points, **Then** the line is broken there, not joined.
3. **Given** no rows, **Then** it reads "no data" as today.

---

### User Story 5 - Looked at, on the live stack (Priority: P2)

**Acceptance Scenarios**:

1. **After deployment**, `/api/v1/features/timeseries` for `binance` `BTCUSDT` at 15m returns `cvd_base`, and the pane
   draws it; a screenshot, light and dark, is kept under `docs/ui/` and looked at.

### Edge Cases

- A bar of zero volume: `delta_base` 0 and `normalized_delta_base` absent; a quiet bar is data for the sum.
- A series whose first bar is the start of its first run: `cvd_base` starts at that bar's delta.
- A bar present with `trade_count` 0: delta 0, no break (nothing traded is not a missed trade).
- Two bars with the same `open_time_ns` (a corrected bar): the later one wins, as the bar reader decides.
- A timeframe change: each timeframe has its own runs; they are not comparable across timeframes.
- Very large sums: `Decimal` in, float stored, as the features table stores.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A pure function MUST turn a series' final bars into flow rows at each bar's close, from the bars' own stored aggressor volumes; it MUST NOT read a trade.
- **FR-002**: `delta_base = aggressive_buy_base − aggressive_sell_base`; `cvd_base` the running sum within a run; `normalized_delta_base` absent when `volume_base` is zero; `cvd_base_acceleration` absent in a run's first bar.
- **FR-003**: A row at bar `t` MUST depend only on bars at or before `t`, and a forming bar MUST produce none.
- **FR-004**: A run MUST end at a missing bar and, for sequential-id venues, at a trade-id discontinuity; a bar whose id span differs from its trade count MUST produce no row.
- **FR-005**: Rows MUST be written by the worker pass, once, after the latest row on record, for every timeframe.
- **FR-006**: The new feature names MUST be `*_base` and registered with a `FeatureSpec` that states the unit and the deviation from §15.4; no row MAY be named `cvd` or `delta_notional`.
- **FR-007**: The CVD pane MUST draw `cvd_base`, MUST break the line where `cvd_run` changes, and MUST read "no data" with no rows.
- **FR-008**: After deployment the live API MUST serve `cvd_base` for the BTCUSDT 15m bars on record.
- **FR-009**: The deviation from notional MUST be recorded in an ADR with the way back.
- **FR-010**: A screenshot of the live pane, light and dark, MUST be kept under `docs/ui/`.

### Key Entities

- **Flow row**: one bar's `delta_base`, `cvd_base`, `normalized_delta_base`, `cvd_base_slope`, `cvd_base_acceleration`, `cvd_run`, at its close.
- **Run**: consecutive bars of one series with no missing bar and no detectable missed trade; `cvd_run` counts them.

## Success Criteria *(mandatory)*

- **SC-001**: With bars of buy/sell volumes (10,4), (6,6), (2,8), `delta_base` is 6, 0, −6 and `cvd_base` 6, 6, 0.
- **SC-002**: Appending later bars leaves the rows at and before `t` byte-identical.
- **SC-003**: Removing the middle bar of three yields two runs and no `cvd_base` summed across the gap.
- **SC-004**: A second worker pass over the same bars writes zero rows.
- **SC-005**: Measured on the live bars on 2026-10-04 (before this was relied on): Binance BTCUSDT 1m, 18,591 of 18,597 bars have `last − first + 1 == trade_count` and 18,586 of 18,587 consecutive pairs are id-contiguous; ETHUSDT likewise (15,665 of 15,672; 15,663 of 15,664). Bybit ids are not numeric and OKX ids are numeric but not sequential (2,682 of 2,734 bars disagree), so the id checks apply to Binance only and are a **registry flag**, not an assumption.
- **SC-006**: The live screenshots exist and were looked at.

## Assumptions

- The bar table's aggressor split is correct as stored (it is the bar builder's output, tested under REQ-WP-005).
- Base-unit CVD is acceptable until the quote split is stored; the owner can reverse this ([[ADR-068]]).
- History exists from each series' ingest start; there is no notional CVD for it and none is invented.
