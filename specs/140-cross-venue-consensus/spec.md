---
traces: [REQ-WP-091]
status: draft
---

# Feature Specification: Cross-venue consensus mid and venue basis

**Feature Branch**: `140-cross-venue-consensus`

**Created**: 2026-10-06

**Status**: Draft

**Input**: [[REQ-WP-091]] — PRD §17.1, §17.3, §17.2, §44A.15; the owner's direction of 2026-10-04.

## Context

The owner asked whether the chart should show an average across all sources. The PRD says:

- §17.1 **Consensus price**: median of normalized mids from selected high-liquidity venues; volume/depth-weighted median is experimental.
- §17.3 **Cross-venue basis**: `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)`.
- §17.2 lead-lag includes DEX marginal return; §44A.15 treats DeFi as context, not price.

The chart and API are per-venue (`/chart/:venue/:symbol`, `GET /bars` with `venue` and `symbol`). No consolidated bar series is defined.

### Facts read from the code

- `crossvenue/` ([[REQ-WP-016]], implemented) has `consensus_mid(quotes, registry, at_ns, staleness_ns)` — median over fresh quotes of ≥2 venues for one asset; quote later than instant or too old is excluded with reason; one venue is refused.
- `basis_bps`, executable basis, fragmentation table exist in the library.
- **Nothing outside the library calls it**: no API route, no pipeline pass, no page.
- It needs **mids** (top-of-book quotes), but the ingest reads trades only — no venue's mid is available.
- Book subscription (Binance `bookTicker`, Bybit/OKX tickers) is separate work ([[REQ-WP-011]]) and is the same subscription OFI/depth-imbalance panes wait for.

### Design decisions from these facts

1. **Consensus is computed from quotes at each bar's close**, not continuously. A bar's consensus uses quotes available at its close time (no look-ahead).
2. **The consensus line is an optional chart layer** (off by default), drawn over candles at each bar's consensus value where ≥2 venues contribute.
3. **The venue basis is a lower pane** showing `10000 * (mid_i / consensus_mid - 1)` for the viewed venue, named `venue_basis_bps` to avoid collision with `basis_bps` (derivatives basis).
4. **Mixed instrument types** (Binance spot, Bybit/OKX perps): the spec decides a stated rule — consensus per market type (spot with spot, perp with perp), since normalizing across types blends spot-perp basis into consensus.

### What this is not

- DeFi in consensus (DEX enters lead-lag and executable basis, needs DEX ingest not running in compose).
- Consolidated bar series.
- Book subscription itself (separate requirement, same as OFI/depth).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consensus mid library correctness (Priority: P1)

**Why this priority**: Foundation for everything; pure function, fully testable in isolation.

**Independent Test**: Call `consensus_mid` with fixture quotes and verify median, exclusions, refusals.

**Acceptance Scenarios**:

1. **Given** quotes from two venues for one asset at instant `t`, **When** `consensus_mid` is called, **Then** it returns the median of the two fresh mids.
2. **Given** quotes from three venues, **Then** median of three fresh mids.
3. **Given** a stale quote (older than `staleness_ns`), **Then** it is excluded and the reason is stated.
4. **Given** a quote with timestamp later than `at_ns`, **Then** it is excluded and the reason is stated.
5. **Given** only one venue with a fresh quote, **Then** the function refuses (returns error/refusal) — no one-venue "consensus".
6. **Given** the same quotes at `t`, **When** later quotes are appended, **Then** the consensus at `t` is unchanged (no look-ahead).

---

### User Story 2 - API serves consensus and venue basis (Priority: P1)

**Why this priority**: Frontend needs data; same endpoints serve chart.

**Independent Test**: Call the new API endpoints with fixture data.

**Acceptance Scenarios**:

1. **GET `/api/v1/consensus?venue=&symbol=&timeframe_ns=&at_ns=`** returns per-bar consensus mids for the window, with venue count and refusal reasons where <2 venues.
2. **GET `/api/v1/features/timeseries?feature=venue_basis_bps&...`** returns the viewed venue's basis to consensus for each bar.
3. Both endpoints respect `at_ns` (point-in-time) and `as_of_ns` (no look-ahead).
4. Windows: 4h, 24h, 7d (same as volume profile); other windows refused.

---

### User Story 3 - Chart draws consensus line (Priority: P1)

**Why this priority**: User-facing feature; visible on chart.

**Independent Test**: Render chart with consensus data; verify line drawn at bar mids where ≥2 venues, absent with reason where <2.

**Acceptance Scenarios**:

1. **Given** consensus data and layer on, **Then** a line connects consensus mids at each bar's close (time = bar close, price = consensus mid).
2. **Given** bars where <2 venues contributed, **Then** no line segment there; a notice states "consensus unavailable: only N venue(s)" at those bars.
3. **Given** layer off, **Then** nothing extra drawn.
4. Line style distinct from channel lines; visible in light/dark.

---

### User Story 4 - Lower pane draws venue basis (Priority: P1)

**Why this priority**: Completes the cross-venue view.

**Independent Test**: Render pane with `venue_basis_bps` data; verify values and registration.

**Acceptance Scenarios**:

1. **Given** `venue_basis_bps` data, **Then** pane draws it as a line series (like CVD) aligned to bars.
2. Feature name is `venue_basis_bps` (not `basis_bps`); registered with `FeatureSpec` (unit: bps, cadence: bar close).
3. Mixed types: consensus per market type (spot venues together, perp venues together); viewed venue's basis uses its type's consensus.
4. Light/dark screenshots on running stack kept under `docs/ui/`.

---

### User Story 5 - Mixed instrument types rule (Priority: P2)

**Why this priority**: Design decision that affects all venues; must be explicit and tested.

**Independent Test**: Fixture with Binance spot + Bybit/OKX perps; verify consensus groups and basis calculation.

**Acceptance Scenarios**:

1. Consensus is computed **per market type**: spot venues together, perp venues together.
2. Viewed venue's basis uses the consensus of its own market type.
3. Test pins this behavior; no silent blending of spot and perp mids.

---

### Edge Cases

- One venue in a market type: consensus refused, line absent, notice states reason.
- Stale quotes at bar close: excluded, count drops, line may have gaps.
- Quote exactly at bar close: included (≤ `at_ns`).
- No quotes at all for a bar: consensus unavailable, gap in line.
- Registry maps venues to assets; only venues for the chart's asset contribute.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `consensus_mid` MUST be called at each bar's close with quotes available at that instant; MUST return median of fresh mids from ≥2 venues; MUST refuse with reason if <2 venues; MUST exclude stale or future quotes with reason.
- **FR-002**: API MUST serve per-bar consensus mids for 4h/24h/7d windows; MUST include venue count and refusal reasons per bar.
- **FR-003**: API MUST serve `venue_basis_bps` as a feature timeseries; MUST use viewed venue's mid vs its market-type consensus; MUST respect `at_ns`/`as_of_ns` (no look-ahead).
- **FR-004**: Chart MUST draw consensus line as optional layer (off by default); MUST draw segments only where ≥2 venues contributed; MUST show notice at gaps with reason.
- **FR-005**: Lower pane MUST draw `venue_basis_bps` for viewed venue; feature name MUST be `venue_basis_bps`; MUST be registered with `FeatureSpec` (unit: bps, cadence: bar close, source: cross-venue consensus).
- **FR-006**: Consensus MUST be computed per market type (spot/perp); viewed venue's basis uses its type's consensus; a test MUST pin this rule.
- **FR-007**: Screenshots of chart with consensus line and basis pane, light and dark, MUST exist under `docs/ui/`.

### Key Entities

- **ConsensusMid**: `{ bar_close_ns, consensus_mid, venue_count, refusal_reason? }` per bar.
- **VenueBasisPoint**: `{ bar_close_ns, venue_basis_bps }` per bar for the viewed venue.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For fixtures of 2/3 venues, consensus = median of fresh mids; stale/future excluded with reason; one venue refuses.
- **SC-002**: Consensus at `t` unchanged when later quotes appended (no look-ahead test).
- **SC-003**: API returns consensus and basis for windows; refusal reasons present where <2 venues.
- **SC-004**: Chart draws line at consensus mids; gaps where <2 venues; notice at gaps.
- **SC-005**: Pane draws `venue_basis_bps`; feature registered correctly; mixed-type fixture works per rule.
- **SC-006**: Existing tests pass; traceability clean.

## Assumptions

- Book subscription (top-of-book quotes) is a separate requirement ([[REQ-WP-011]]) and must land first.
- The `crossvenue` library's `consensus_mid` already enforces no look-ahead; we reuse it.
- Volume/depth-weighted median is experimental and out of scope.
- The registry (`instrument_metadata`, [[REQ-WP-060]]) maps venues to assets and market types.