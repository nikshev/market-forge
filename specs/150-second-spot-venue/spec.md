---
traces: [REQ-WP-098]
status: draft
---

# Feature Specification: A second spot venue, so the Binance spot panes have a consensus

**Feature Branch**: `150-second-spot-venue`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-098]] -- owner's choice 2026-10-11; PRD §17.1, §17.3, §27.3. Builds on [[REQ-WP-093]], [[REQ-WP-095]], [[REQ-WP-096]].

## Context

### Facts measured on 2026-10-11, not assumed

1. After REQ-WP-096 the three Binance spot series read `Venue basis: absent: only 1 venue(s) could contribute...` -- true, and
   the one place a pane is still empty for want of a producer rather than of a source.
2. OKX lists spot `BTC-USDT`, `ETH-USDT` and `SOL-USDT`; the project's trade ingest, market-type rule (`okx_market_type`:
   `BASE-QUOTE` is spot), connector and normalizers already handle an OKX instrument of either kind.
3. OKX's `books` channel serves a spot instrument as it serves a swap, with the same `seqId`/`prevSeqId` chain (which the
   book now reads, [[REQ-WP-095]]); **a spot size is in the base coin, a swap's is in contracts** -- the conversion the book
   stream applies to OKX must therefore depend on the instrument's kind.
4. OKX's perpetuals for ETH and SOL (`ETH-USDT-SWAP`, `SOL-USDT-SWAP`) are not polled today; the spot series are shown
   their venue's perpetual for open interest, funding and basis, which needs them.
5. The worker covers every series the bars table holds, so the new series add channels, signals and notary records: more
   work per cycle, with no change to how it is done.

### What this is not

A new venue's perpetual as a *series* (only OKX's BTC swap is one), Bybit spot, and any change to how the consensus is
computed (the library's median is unchanged).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The Binance spot venue-basis pane has a line (Priority: P1)

Someone opens Binance BTCUSDT (spot), selects Venue basis, and sees the basis to the BTC spot consensus of Binance and OKX.

**Independent Test**: after the new ingest, books and the worker's passes have run, the venue-basis read for the Binance and the
OKX spot series returns points equal to the formula over the stored mids; `make panes-report` has `data` there.

**Acceptance Scenarios**:

1. **Given** quotes from both venues for BTC spot, **When** the pass runs, **Then** a consensus row with `venue_count` 2 and a price is stored under `BTCUSDT` and under `BTC-USDT`.
2. **Given** that row, **When** the venue-basis read is made for Binance and for OKX, **Then** each point is `10000 * (mid / consensus - 1)` for that venue's stored mid.

### User Story 2 - OKX spot is a market like the others (Priority: P1)

**Independent Test**: the markets read lists OKX `BTC-USDT`, `ETH-USDT`, `SOL-USDT` as `spot`; bars exist and every configured timeframe is resampled.

**Acceptance Scenarios**:

1. **Given** the three new ingest services, **When** they run, **Then** each registers its market once and builds bars.
2. **Given** bars, **When** the worker runs, **Then** it writes the flow features for the new series like any other.

### User Story 3 - A spot book is not read as contracts (Priority: P1)

**Independent Test**: the same OKX `books` frame shape for a spot instrument and for a swap gives different sizes: the spot's are the frame's, the swap's are scaled by its contract value; a swap with no contract value is refused.

**Acceptance Scenarios**:

1. **Given** a recorded spot frame, **When** normalised, **Then** its sizes equal the frame's.
2. **Given** a swap frame and a contract value, **When** normalised, **Then** its sizes are the frame's times that value.
3. **Given** a swap frame and no contract value, **When** normalised, **Then** it is refused with the instrument named.

### User Story 4 - The new series are shown their perpetual's derivatives (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the OKX collector, **When** it runs, **Then** it polls `BTC-USDT-SWAP`, `ETH-USDT-SWAP` and `SOL-USDT-SWAP`, and the worker writes open interest, funding and basis for the OKX spot series from them.

### Edge Cases

- A symbol present on one venue's spot and the other's under a different name (`BTCUSDT` / `BTC-USDT`): the consensus is stored under both, and the registry (not the name) decides they are one asset.
- One of the two venues is down: the consensus falls back to a refusal for that minute, with the library's reason; the pane says so.
- OKX spot `books` for three symbols plus the swap in one subscription: one connection, four books, each with its own market type label.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Three ingest services (one symbol each) ingest OKX spot `BTC-USDT`, `ETH-USDT`, `SOL-USDT` into the existing bars pipeline; configured through the same environment pattern as the existing ones.
- **FR-002**: The OKX collector's book stream covers the three spot instruments and the swap; a book's market type label is per instrument (spot or perp), not per venue.
- **FR-003**: OKX book sizes are converted with the instrument's contract value for a swap and left as they are for a spot instrument; a swap with no usable contract value is refused.
- **FR-004**: The perpetual mapping gives each OKX spot series its pair's perpetual; the OKX collector polls and listens to every perpetual so named.
- **FR-005**: The deployment's market list for the consensus includes the three OKX spot markets, so each spot group has two venues.
- **FR-006**: Existing containers are not recreated by starting the new services; configuration for them is documented.
- **FR-007**: Every file added carries a requirement trace.

### Key Entities

- **Series list** (`context/sources.py`): every `(venue, symbol, market type)` the deployment ingests; the perpetual mapping and the book symbols derive from it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `make panes-report` at 1m: all six spot series (Binance and OKX x BTC/ETH/SOL) have `data` in Venue basis.
- **SC-002**: For each spot group, over a recorded hour, every consensus row has `venue_count` 2 except minutes with a stated refusal.
- **SC-003**: The spot/swap size rule has a test that fails if either is swapped.
- **SC-004**: The start times of every pre-existing container are unchanged by starting the new ingest services.

## Assumptions

- OKX's public spot websocket is reachable from this host (as its swap channels are, probed 2026-10-11).
- The worker's cycle gets longer with three more series; this is accepted and measured, not designed away.
