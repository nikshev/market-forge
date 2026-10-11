---
traces: [REQ-WP-095]
status: draft
---

# Feature Specification: The order-flow panes and the venue quotes are fed by a top-of-book subscription

**Feature Branch**: `147-book-subscription`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-095]] -- owner's direction 2026-10-11; PRD §10.3, §11.1, §15.1, §15.3, §17.1, §27.3. Principle I, II, [[ADR-070]]; shares the collector of [[REQ-WP-093]] (spec 145).

## Context

### Facts measured on 2026-10-11, not assumed

1. **No order book exists anywhere in the system**: the ingest subscribes to trades only. The consumers are built and tested -- `OFITracker` (`features/ofi.py`), `depth_imbalance_levels` (`features/instant.py`), `BookService` (`book/service.py`), the `quotes` table (`tables/quotes.py`) -- and have no feed. This is also why the cross-venue consensus has "no venue's mid" ([[REQ-WP-091]]).
2. **The streams connect from this host.** Binance spot `<symbol>@depth<N>@<ms>` and OKX `books5` carry whole top-of-book snapshots (Binance frames `{lastUpdateId, bids, asks}`); Bybit `orderbook.<N>.<symbol>` opens with a snapshot and continues with deltas, which the existing `BookService` already handles (gap detection, resnapshot). Reading the top ten levels never needs §11.1's full-depth reconstruction.
3. **The deployment's markets**: Binance BTC/ETH/SOL are spot, Bybit BTC and OKX BTC are perpetuals. A book belongs to the market it was subscribed on.
4. **The panes read bar-close features**, so what is stored must be reducible to "the value as of a close" without the raw book: a per-minute summary, finalised in event time, suffices.
5. **Cost matters.** At 100 ms across five markets the raw book is the largest data in the system; nothing required needs it (ADR-070 point 4).

### What this is not

Delta-stream reconstruction, deep-book features (walls, absorption, §15.5-15.7), a raw-book archive, and any change to the consensus code, the API or the web app.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - OFI and depth imbalance show their series (Priority: P1)

Someone opens the Binance, Bybit or OKX BTC chart, selects OFI (1m) or Depth imbalance (10), and sees a line.

**Why this priority**: the owner's request; two of the nine panes.

**Independent Test**: after the collector has run and the worker has finished a pass, the features endpoint carries both features at the viewed timeframes and the panes are enabled; imbalance values lie in [-1, 1].

**Acceptance Scenarios**:

1. **Given** a scripted frame sequence across a minute boundary, **When** the minute is finalised, **Then** its OFI, depth imbalance and mid equal a hand calculation.
2. **Given** the stored summaries, **When** the worker computes a bar, **Then** the value equals the summary of the last minute that closed at or before the bar's close.

---

### User Story 2 - A minute is finalised from what was knowable before its boundary (Priority: P1)

**Why this priority**: Principle I.

**Independent Test**: frames after the boundary do not change the finalised minute; the worker's value at a close does not change when later summaries are appended.

**Acceptance Scenarios**:

1. **Given** frames with event times on both sides of a boundary, **When** the minute is finalised, **Then** only the earlier ones enter it.
2. **Given** a later summary appended, **When** the bar at the earlier close is recomputed, **Then** it is identical.

---

### User Story 3 - A thin or empty minute is not a balanced one (Priority: P1)

**Independent Test**: a reconnect leaves a minute with zero frames; it is stored with a count of zero and the worker writes nothing for it.

**Acceptance Scenarios**:

1. **Given** no frame in a minute, **When** finalised, **Then** the summary carries a frame count of zero and no OFI or imbalance value.
2. **Given** a summary with a zero count, **When** the worker runs, **Then** no row is written for bars that rest on it.

---

### User Story 4 - The venues' quotes exist (Priority: P2)

**Independent Test**: after the collector has run, `quotes` has one row per market per minute close, with exchange and receive time apart.

**Acceptance Scenarios**:

1. **Given** a finalised minute with a valid book, **When** stored, **Then** a quote (bid, ask, mid, exchange time at the boundary's last frame, receive time) is written.
2. **Given** a crossed or empty book, **When** received, **Then** it is refused with a reason and produces no quote and no summary value.

### Edge Cases

- **A crossed book** (best bid at or above best ask) or one with an empty side: refused with a reason, never stored as a quote; the minute's count excludes it.
- **A reconnect mid-minute**: frames before and after are both valid snapshots; there is no delta continuity to lose, so none is claimed; the OFI increment across the gap is **not** counted (the tracker is reset at a reconnect, because the book may have moved arbitrarily), and the minute's count says how many observations it really had.
- **A stalled stream** that stops sending: detected by a stated window, reconnected with capped backoff; metrics show it.
- **A symbol absent on a venue**: refused at start with a clear message, not silently skipped.
- **Clock skew** between a frame's venue timestamp and receipt: refused beyond a stated bound, never stored.
- **Sampling**: snapshots arrive at 100-1000 ms; the OFI is computed from sampled snapshots and the registration says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The collector subscribes, per venue and market, to a snapshot-style top-of-book stream for the configured symbols and normalises each frame into a `BookSnapshot` (§10.3). Binance's series use the spot book; Bybit's and OKX's use the perpetual's.
- **FR-002**: A crossed, empty-sided or non-positive book is refused with a reason and affects nothing.
- **FR-003**: For each symbol the collector feeds `OFITracker` and `BookService` and, when the first frame of the next minute arrives, finalises the minute that ended: 1-minute OFI, depth imbalance over the top 10 levels, the quote (bid, ask, mid) at the minute's last valid frame, and the number of frames it rested on.
- **FR-004**: The tracker is reset at a reconnect, so no OFI increment spans a gap.
- **FR-005**: Summaries are stored append-only in a `book_minutes` table (venue, symbol, minute close, OFI, depth imbalance, mid, frame count, event times and ingest time apart); quotes are also written to the existing `quotes` table.
- **FR-006**: A minute with no valid frame is stored with count zero and no values.
- **FR-007**: The worker writes `ofi_1m` and `depth_imbalance_10` at each bar's close from the summary of the last minute closed at or before it, for every timeframe; a zero-count or missing summary writes nothing; the worker is the only writer of `feature_snapshots`.
- **FR-008**: A value at a close is unchanged by summaries or frames appended later (a test).
- **FR-009**: The registrations of `ofi_1m` and `depth_imbalance_10` state the sampling (snapshots at the stream's interval, top of book / top ten levels).
- **FR-010**: A stalled stream is detected and reconnected; reconnects, refused frames and frames per minute are metrics; the collector's CPU is measured and the stream interval chosen to fit the host.
- **FR-011**: The six trade features and the features of specs 145 and 146 keep their values and counts.
- **FR-012**: Every new file carries a requirement trace.

### Key Entities

- **BookSnapshot** (§10.3) as the project defines it; **Minute summary**; **Quote** (existing).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a recorded frame per venue the normalised snapshot's best bid, best ask and level count match the frame (3 of 3).
- **SC-002**: For a scripted sequence the finalised minute's OFI, imbalance and mid equal the hand calculation exactly (Decimal arithmetic), and appending later frames changes nothing.
- **SC-003**: Zero rows are written for zero-count minutes (a reconnect fixture).
- **SC-004**: On the running stack after the first worker pass following 24 hours of collection, both panes are enabled for the three BTC series, with at least 95% of bars carrying a value and all imbalances in [-1, 1].
- **SC-005**: `quotes` has a row per market per minute for the collection window (gaps only where the stream was down, counted by the metric).
- **SC-006**: With five books subscribed the host's measured load (collector CPU, MinIO health, worker cycle time) stays within the bound the plan sets, and the live stack is not degraded (no 503 from the object store, worker cycle within its usual 28-35 minutes).

## Assumptions

- Snapshot depth of 10 levels per side suffices for `DI_10`; deeper bands (§15.1's 25/50) are a later requirement.
- A sampling interval of 250-1000 ms is acceptable for a 1-minute OFI; the plan picks per venue from what the host carries and records it.
- Binance's spot partial-depth stream is the right book for a spot series; the futures book is not substituted.
- OKX `books5` (5 levels) cannot give a ten-level imbalance; the plan chooses `books` (400 levels, snapshot then updates) or a `books50-l2-tbt`-style channel, or records that the OKX series' imbalance is over five levels and says so in the feature's source. This is the one place where a venue's stream shape may force a delta-handling step, and it is flagged for the plan, not decided here.
