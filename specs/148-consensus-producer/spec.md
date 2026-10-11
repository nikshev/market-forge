---
traces: [REQ-WP-096]
status: draft
---

# Feature Specification: The venue-basis pane has a consensus

**Feature Branch**: `148-consensus-producer`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-096]] -- owner's direction 2026-10-11; PRD §17.1, §17.3, §27.3. Principle I, [[REQ-WP-091]] (spec 140), [[REQ-WP-095]] (spec 147), [[ADR-070]].

## Context

### Facts measured on 2026-10-11, not assumed

1. **The reading side exists, the writing side does not.** The API's venue-basis and consensus reads (`select_venue_basis`, `get_consensus`) merge two tables, `quotes` and `consensus`; `crossvenue/consensus.py` computes the median with its refusals. **Nothing in `src/` writes either table**; the only writers are the test helpers.
2. **`quotes` is written by spec 147** (one row per market per minute close); this requirement writes `consensus`.
3. **Consensus is per market type, never blended** (spec 140, FR-006): spot venues against the spot consensus, perpetuals against the perpetual consensus.
4. **What the deployment's venues allow**: Bybit BTC and OKX BTC are both perpetuals of the same pair, so BTC has a perpetual consensus of two venues. Binance's series are spot and no other spot venue is ingested, so a spot consensus has one venue and is refused ("a median over one venue is that venue's mid wearing a better name").
5. **Every timeframe's bar close is a minute close**, so writing one consensus row per minute close serves every timeframe the chart can show.

### What this is not

Changing the consensus maths, the API, the web app, or ingesting a new venue. Adding a second spot venue is recorded as an option and left to the owner.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The venue-basis pane shows for the perpetual venues (Priority: P1)

Someone opens the Bybit or OKX BTC chart, selects Venue basis, and sees the venue's basis to the perpetual consensus; the consensus line can be switched on.

**Why this priority**: the owner's request; the pane exists and is empty.

**Independent Test**: after the collector and the worker have run, the venue-basis read for Bybit and OKX BTC returns points equal to `10000 * (mid / consensus - 1)` from the stored mids.

**Acceptance Scenarios**:

1. **Given** quotes from two perpetual venues at a minute close, **When** the pass runs, **Then** a consensus row exists with the median mid and `venue_count` 2.
2. **Given** the stored consensus and quotes, **When** the venue-basis is read, **Then** each point equals the formula for the viewed venue.

---

### User Story 2 - A refusal is stored with its reason (Priority: P1)

**Why this priority**: the absence of a line must be explainable; the Binance spot panes depend on it.

**Independent Test**: with one venue of a market type, the pass stores a row with no price and a reason; the Binance read returns that reason.

**Acceptance Scenarios**:

1. **Given** one spot venue only, **When** the pass runs, **Then** a row with `consensus_mid` null, `venue_count` 1 and a non-empty reason is stored.
2. **Given** that row, **When** the Binance read is requested, **Then** it reports the refusal and no number.

---

### User Story 3 - The consensus at a close does not depend on later quotes (Priority: P1)

**Independent Test**: appending quotes after a close leaves that close's row unchanged; a stale quote is excluded with a reason.

**Acceptance Scenarios**:

1. **Given** a stored fixture, **When** later quotes are appended and the pass is re-run, **Then** the earlier close's consensus is identical.
2. **Given** a quote older than the staleness bound, **When** the consensus is computed, **Then** it is excluded and the venue count reflects it.

---

### User Story 4 - The pass is idempotent (Priority: P2)

**Independent Test**: running the pass over the same range twice stores each close once.

**Acceptance Scenarios**:

1. **Given** a stored range, **When** the pass runs again, **Then** no row is added.

### Edge Cases

- A venue's symbol with no asset in the registry: not part of any consensus, reported once per pass, never guessed.
- One venue down: the consensus continues on the rest and `venue_count` says how many contributed; below two it is refused.
- A gap in the quotes: the closes in it get refusal rows (reason: no fresh quotes), not skipped silently.
- A clock-ahead quote: excluded as later than the close, with the library's reason.
- Backfill after an outage: closes are computed in order from stored quotes; the result is the same as live (replay parity).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The worker gains a pass that, for every (asset, market type) the registry defines and every minute close with quotes, computes the consensus mid through the existing `consensus_mid` from quotes at or before that close and stores one row.
- **FR-002**: A refused consensus is stored with `consensus_mid` null, the venue count and the reason.
- **FR-003**: The asset of a venue's symbol comes from the same registry the API reads.
- **FR-004**: The row's value at a close is unchanged by later quotes (a test); a stale or later quote is excluded with the library's stated reason.
- **FR-005**: The pass is idempotent per (asset, market type, close) with a watermark; it advances only over closes whose quotes have arrived (the newest quote time of the contributing venues).
- **FR-006**: `venue_basis_bps` stays a read-time merge in the API; it is not duplicated into `feature_snapshots`.
- **FR-007**: The worker remains the only writer of `consensus`.
- **FR-008**: Every new file carries a requirement trace.

### Key Entities

- **Consensus row** (existing table): asset, market type, bar close, consensus mid, venue count, refusal reason.
- **Asset registry** (existing): venue symbols to assets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For quote fixtures of two and three venues the stored consensus equals the median to the stored precision (exact, Decimal).
- **SC-002**: One-venue, stale-quote and later-quote cases each store the expected refusal or exclusion with a non-empty reason.
- **SC-003**: Re-running the pass over the same range adds zero rows.
- **SC-004**: On the running stack after the pass, the venue-basis read for Bybit and OKX BTC returns points equal to the formula over the stored mids (all points in a sample, zero differences), and the Binance read returns the refusal reason instead of a number.
- **SC-005**: The consensus at any close is byte-identical before and after appending later quotes.

## Assumptions

- Quotes from spec 147 are present for Bybit and OKX BTC at the minute cadence the pass reads.
- The registry already maps the perpetual BTC symbols of both venues to one asset; the plan confirms it and adds the mapping if it is missing, as configuration, not code.
- Binance spot stays without a consensus until a second spot venue is ingested; this is stated on the page by the refusal reason.
