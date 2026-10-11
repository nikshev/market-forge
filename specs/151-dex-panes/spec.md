---
traces: [REQ-WP-099]
status: draft
---

# Feature Specification: The DEX panes get a source

**Feature Branch**: `151-dex-panes`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-099]] -- owner's choice 2026-10-11; PRD §18.11.2, §18A.4, §19, §27.3. Builds on [[REQ-WP-058]], [[REQ-WP-059]], [[REQ-WP-063]].

## Context

### Facts measured on 2026-10-11, not assumed

1. `make panes-report` ends with two rows reading "no DEX source: this deployment runs no DEX ingest". Everything but the source exists:
   the decoders, `dex_swaps`, `dex_state`, and both features with their window and as-of rules.
2. The public HyperEVM node (`rpc.hyperliquid.xyz/evm`) answers `eth_getLogs` over at most **1000 blocks** (above it:
   `query exceeds max block range 1000`) and **rate limits within seconds** of a burst (`-32005 rate limited`, in a 200 response).
   Each log carries `blockTimestamp`, so no second request per block is needed.
3. The two pools carry about **43 swaps per 500 blocks** (1 s blocks): a handful a minute, so a quiet minute is normal and
   "no swap" cannot be read as "not collecting".
4. Both pools have token0 = WHYPE (`0x5555...5555`, 18 decimals) and token1 = USDC (`0xb883...630f`, 6 decimals); the Uniswap v3
   pool (`0x6c9a...9285`, factory `0xff7b...b072`, fee 500, spacing 10) and the Algebra Integral pool (`0xbe51...d696`,
   factory `0xf77b...b1f3`, spacing 5) emit the identical `Swap` topic.
5. `Swap` carries `liquidity` -- the pool's active liquidity after that swap -- and `liquidity()` gives it at any time; neither needs
   a tick map. [[REQ-WP-063]]'s feature already accepts a `partial_ticks` reading for this reason.
6. Bybit lists `HYPEUSDT` as a linear perpetual; it is the market the pools price.

### What this is not

Other chains or pools, a tick-map reconstruction (depth), USD-denominated flow, and any change to the two features' definitions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Someone sees which way HYPE's pools are leaning (Priority: P1)

Opens Bybit HYPEUSDT, selects DEX swap imbalance, and sees a line of the pools' five-minute signed flow.

**Independent Test**: stored swaps plus polls for every minute of a window give the library's value at the close; a window the collector missed gives none.

**Acceptance Scenarios**:

1. **Given** swaps in `(close - 5m, close]` stored before the close and a poll for each minute, **When** the pass runs, **Then** the value equals `sum(amount0) / sum(|amount0|)` over them.
2. **Given** a swap in the window that was stored after the close, **Then** it is not in that close's value.
3. **Given** a minute of the window with no poll, **Then** there is no value for that close.
4. **Given** every minute polled and no swap, **Then** there is no value (not zero).

### User Story 2 - Someone sees how deep the pool is (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a liquidity reading within three polls before the close, **Then** the active-liquidity value is that reading (of the busiest pool).
2. **Given** none that recent, **Then** there is no value.

### User Story 3 - The chain is read without losing or doubling a swap (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a recorded `eth_getLogs` answer, **Then** every swap becomes a `DexSwapEvent` equal to the decoder's, dated by `blockTimestamp`.
2. **Given** a failing, rate-limited or refused request, **Then** nothing is stored and the next poll asks for the same blocks.
3. **Given** a range wider than 1000 blocks (after downtime), **Then** it is asked for in pieces, and a piece that fails leaves the cursor where the last good piece ended.
4. **Given** a restart, **Then** the cursor is the last stored block, and a swap already stored is not stored again.
5. **Given** a log from an address the registry does not name, **Then** it is refused.

### User Story 4 - The panes report says what is true (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the deployment, **Then** the report shows `data` for HYPEUSDT in both panes and names the remaining series' absence as "no DEX pool is registered for this asset".

### Edge Cases

- A reorg: HyperEVM finality is one block; a swap is stored once it is at least one block behind the head, and `removed: true` logs are refused.
- The node is down for hours: the gap is a window without polls, so the affected closes have no value; nothing is back-filled into a past close's as-of view.
- Both pools quiet for five minutes: no value; the pane is empty because nothing traded, which the report names.
