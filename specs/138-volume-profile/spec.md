---
traces: [REQ-WP-089]
status: draft
---

# Feature Specification: A volume profile beside the price axis, with buy and sell by level

**Feature Branch**: `138-volume-profile`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-089]] — PRD §14.1, §27.2; the owner's direction of 2026-10-04.

## Context

The owner's idea was never volume per candle: it was **volume aggregated by the price levels the chart shows, at the side of the
chart, as delta clustering** — for each level, how much traded and how much of it was aggressive buying and selling. The Volume
pane under the chart is volume by *time* and cannot show a level; the owner said so on seeing it.

### Facts read from the code, which decide the design

- `volume/profile.py` ([[REQ-WP-012]]) builds a `VolumeProfile` from `TradeEvent`s: bins on a fixed arithmetic grid from an anchor,
  each `Bin` with `volume`, `buy_volume`, `sell_volume` (from the aggressor side, "never from anything else"), a trade count, the
  POC (ties to the lower price), and the value area by ADR-028. Tested. It reads trades, and **no trade is stored**.
- A stored bar carries the aggressor split for the **whole bar** and no price inside it. A profile from bars (spreading a bar's
  volume across high-low) is what §14.1 forbids; so the price bins have to be collected from the trades, **from now on**: there is
  no history to recover them from. (The raw frame archive holds the frames; replaying it is a later backfill, not this.)
- The ingest hands each trade to the `BarBuilder` and nothing else; the daemon constructs the builder and the bar sink in
  `ingest_main.py`; `flush_bars` and `bars_pending` are the seams the daemon commits through.
- `lightweight-charts` 4.2.3 has **series primitives** (`attachPrimitive`): a custom renderer drawn on the chart's own canvas, given
  the series' `priceToCoordinate`, redrawn as the reader pans, zooms or the price scale autoscales. A DOM overlay would have to be
  re-positioned on each of those; a primitive is positioned by the library.
- The chart already has a `volume_profile` layer (in §27.2's vocabulary and in the default layers) and a `profile` prop that only drew
  price lines; nothing feeds it.
- The API reads tables whole per request and filters in Python (the repository pattern); a point-in-time read exists on a table's
  event-time column.
- A restart loses the block in progress; for Binance the trade ids show it (an id span that is not the trade count).

### What a block is, and why 5 minutes

The ingest aggregates per **5-minute block** and per price bin: `buy`, `sell`, `unknown`, trades. Per-minute-per-tick would be about
fifty million rows a year per symbol; 5-minute blocks of coarse bins are a few thousand a day. A profile is for windows of 4 hours
and more, so five minutes loses nothing a profile can show, and a block is knowable only at its close, so a profile as of `t` uses
whole blocks closed at or before `t` (Principle I).

### What this is not

Not a backfill, not the lower pane, not the notional split, not HVN/LVN or the other §14.1 outputs beyond POC, VAH, VAL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The ingest collects price bins (Priority: P1)

**Independent Test**: feed trades to the builder and read the blocks it closes.

**Acceptance Scenarios**:

1. **Given** trades with known prices and aggressor sides in a 5-minute block, **When** the block closes, **Then** one row per
   price bin: `buy` the sum of buy-aggressor base quantity, `sell` of sell-aggressor, `unknown` of the rest, and the trade count.
2. **Given** a trade exactly on a block boundary, **Then** it belongs to the block that opens there; **given** a trade for a block
   already closed, **Then** it is discarded and counted (the block is not amended).
3. **Given** a Binance block whose ids are `first..last` and whose trade count is not `last - first + 1`, **Then** no rows are
   written for it and it is counted; **given** a venue without sequential ids, **Then** the block is written.
4. **Given** a price exactly on a bin edge, **Then** it falls in the upper bin (the profile builder's rule).
5. **Given** the same trades in any order within the grace period, **Then** the same rows.

---

### User Story 2 - A profile from the bins, as of an instant (Priority: P1)

**Acceptance Scenarios**:

1. **Given** stored bins, a window and an instant, **Then** the profile sums the blocks closed in `(instant - window, instant]`, with
   POC, VAH, VAL and the value area from the same code the trade-level profile uses, equal to the trade-level profile for the
   same trades on the same grid.
2. **Given** blocks later than the instant, **Then** they change nothing (no look-ahead).
3. **Given** data covering less than the window, **Then** the response says how much it covers (`covered_ns`, `covers_from_ns`) and
   `complete` is false.
4. **Given** stored rows of two bin widths, **Then** only the most recent width is used and the response says rows were left out.
5. **Given** no bins, **Then** there is no profile (404 with a reason), never an empty or zero one.

---

### User Story 3 - The API serves it (Priority: P1)

**Acceptance Scenarios**:

1. **When** `GET /api/v1/volume-profile?venue=&symbol=&window=24h&at_ns=` is called, **Then** it returns the bins (low, high, buy, sell,
   unknown, trades), the POC index, the value-area edges, the instant, the window, the width and the coverage; the window is one of
   4h, 24h, 7d; any other is a 422.
2. **Given** `at_ns` is omitted, **Then** the instant is the latest closed block.

---

### User Story 4 - The chart draws it at the side, on its price levels (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a profile and the `volume_profile` layer on, **Then** horizontal bars are drawn on the chart canvas, anchored at the right edge of the plot area beside the price axis and growing leftwards (the busiest bin at most a quarter of the plot's width), one
   per bin, each at the bin's price range on the chart's own price scale, as long as its volume, split into the buy and sell parts in
   two colours, with the POC and the value area marked.
2. **Given** the reader pans, zooms or the price scale autoscales, **Then** the bars stay on their levels without any code of the page running.
3. **Given** the layer off, **Then** nothing is drawn; **given** no profile yet, **Then** the chart says so ("collecting since ..."), not an
   empty profile.
4. **Then** a window selector (4h, 24h, 7d) with 24h the default, and the coverage in words ("covers 3 h 20 m of 24 h").
5. **Then** light and dark follow the palette.
6. **Given** a deep link with an instant (`at`), **Then** the profile is as of that instant (AS-SEEN-THEN's own rule); otherwise the latest closed block.

---

### User Story 5 - Looked at, on the live stack (Priority: P2)

1. After deployment, on BTCUSDT 15m, a screenshot with the profile, light and dark, is kept under `docs/ui/` and looked at; it states its coverage.

### Edge Cases

- A very narrow or very wide price range: bars scale to the busiest bin; bins outside the visible price range are not drawn.
- One bin only: valid (value area is the whole profile and says so).
- A bin with only unknown-aggressor volume: drawn in a third, neutral colour.
- A symbol whose price changed so much that the derived bin width is no longer sensible: widths are recorded per row, and a profile uses the latest.
- Ties for POC: the lower price, recorded.
- Resize: the primitive redraws with the chart.
- Many bins in view: bar heights are the bin's price range, so adjacent bins touch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The ingest MUST aggregate trades per 5-minute block and price bin into buy, sell and unknown base volume and a trade count, using the aggressor side only, and write one row per bin when the block closes.
- **FR-002**: A block whose trade ids show missed trades (venues flagged `sequential_trade_ids`) MUST NOT be written, and MUST be counted.
- **FR-003**: Each row MUST carry its bin width; a profile MUST use one width only, the most recent, and say if rows were left out.
- **FR-004**: A profile as of `t` MUST use only blocks closed at or before `t`, over the window `(t - window, t]`, and MUST equal the trade-level profile (REQ-WP-012) for the same trades on the same grid, POC and value area included.
- **FR-005**: A profile MUST report how much of its window the data covers; it MUST NOT be presented as the full window when it is not.
- **FR-006**: The API MUST serve it for 4h, 24h and 7d and refuse other windows; with no bins it MUST answer 404 with a reason.
- **FR-007**: The chart MUST draw the profile with a series primitive: bars on their own price levels, buy and sell in two colours, POC and the value area marked, following the price scale without page code.
- **FR-008**: The bin width MUST be configurable per symbol (Principle X) through `CHANNELFLOW_PROFILE_BIN_WIDTHS` (`venue:SYMBOL=width,...`), with a stated default derived from the first trade's price (about 2 bps, rounded to a 1-2-5 number); the block length through `CHANNELFLOW_PROFILE_BLOCK_SECONDS`, default 300. Both reach the ingest services through `docker-compose.yml`, `.env.example` and `docs/deployment.md`.
- **FR-009**: A live screenshot, light and dark, MUST be kept under `docs/ui/`.

### Key Entities

- **Block**: a 5-minute window of one symbol's trades, closed once, never amended.
- **Bin row**: `(venue, symbol, block_open, bin_index)` with `bin_width`, `buy`, `sell`, `unknown`, `trades`.
- **Profile response**: the bins of a window as of an instant, with POC, value area and coverage.

## Success Criteria *(mandatory)*

- **SC-001**: For ten trades at known prices in one block, the rows' buy and sell sums equal the hand-computed ones per bin.
- **SC-002**: The profile from stored bins equals `build(trades, anchor=0, ...)` for the same trades (the stored grid is `floor(price / width)` from zero): per-bin `low`/`high` and buy/sell/volume, the POC bin's edges and the value-area edges. (`build` renumbers its bins by position, so bins are compared by their edges, not by index.)
- **SC-003**: Appending a later block leaves the profile as of an earlier instant byte-identical.
- **SC-004**: With 3 hours of blocks and a 24h window the response says `covered_ns` of 3 hours and `complete` false.
- **SC-005**: The existing web and Python tests pass with only the edits each outcome note lists.
- **SC-006**: The live screenshots exist and were looked at.

## Assumptions

- Base-unit volumes, as `profile.py` already uses (`qty_base`).
- Collection starts at deployment; a 7d profile is complete only after seven days.
- A profile as of `t` holds only whole closed blocks, so it lags the live market by up to one block (five minutes).
- A coarse default width of about 2 bps of price, rounded to a 1-2-5 number, is useful on a chart; it is a default, not a constant.
