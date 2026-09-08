---
traces: [REQ-API-001, REQ-WP-009]
status: draft
---

# Feature Specification: Chart and read API

**Feature Branch**: `wp-009-chart`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-API-001 — PRD §28's read API. REQ-WP-009 — candles; channel;
zones; marker; historical snapshot mode; realtime WS.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a signal and see exactly what it saw (Priority: P1)

Following an alert's deep link opens the chart at that instant, showing the
channel **as it stood then** — the immutable snapshot, not a channel refitted
with everything that has happened since.

**Why this priority**: PRD §27.5 calls this "critical" and says it "directly
exposes repaint-like differences and protects research integrity". PRD §2.1
names repainting as the risk the product exists to avoid, and Principle I
forbids look-ahead outright. Every other story here is a way of looking at
data; this one is the reason the product is trustworthy.

**Independent Test**: Store a channel snapshot, let later bars arrive, request
the same instant in both modes, and assert the two differ and that
`AS-SEEN-THEN` matches what was stored.

**Acceptance Scenarios**:

1. **Given** a stored channel snapshot and later bars, **When** `as_seen_then=true` is requested, **Then** the stored snapshot is returned unchanged.
2. **Given** the same instant, **When** `as_seen_then=false` is requested, **Then** a channel fitted over current history is returned, and it may differ.
3. **Given** a request that omits the parameter, **When** it is served, **Then** `as_seen_then` is true.
4. **Given** the chart opened from a deep link, **When** it first renders, **Then** it is in `AS-SEEN-THEN` mode.
5. **Given** the chart in `CURRENT REFIT` mode, **When** it renders, **Then** the mode is stated on screen — a reader must never be unsure which they are looking at.

---

### User Story 2 - Read bars, channels, features and signals (Priority: P1)

The API serves the market data a chart needs: markets, bars over a range,
channel snapshots, feature snapshots and time series, signals with filters, and
one signal in full.

**Why this priority**: PRD §28. Nothing can be drawn without it.

**Independent Test**: Populate a repository with known data and assert each
endpoint's response.

**Acceptance Scenarios**:

1. **Given** bars in the repository, **When** bars are requested for a venue, symbol, timeframe and range, **Then** only bars inside the range are returned, in event-time order.
2. **Given** a limit, **When** more bars match than the limit, **Then** the most recent that fit are returned.
3. **Given** markets, **When** they are requested with a venue filter, **Then** only that venue's are returned.
4. **Given** signals, **When** they are requested by symbol and time range, **Then** only matching ones are returned.
5. **Given** a signal id, **When** its detail is requested, **Then** the decision, channel and feature snapshots are returned, and any later outcome is a separate field.
6. **Given** a request for a symbol nothing is known about, **When** it is served, **Then** the answer is an empty result rather than an error — nothing known is a fact.

---

### User Story 3 - Watch the chart update live (Priority: P2)

A WebSocket subscription names a venue, symbol, timeframe and channels, and
updates arrive for those channels only.

**Why this priority**: PRD §28.7 and REQ-WP-009's last acceptance criterion. P2
because a chart that shows correct history is useful before it updates itself.

**Independent Test**: Subscribe, publish updates on several channels, and
assert only the subscribed ones arrive.

**Acceptance Scenarios**:

1. **Given** a subscription naming `["bars", "signals"]`, **When** a channel update is published, **Then** it is not delivered.
2. **Given** a subscription, **When** a bar closes, **Then** the bar arrives on the `bars` channel.
3. **Given** a malformed subscription message, **When** it is received, **Then** it is rejected with a stated reason and the connection stays usable.
4. **Given** an update for a different symbol, **When** it is published, **Then** the subscriber does not receive it.

---

### User Story 4 - See the setup on the chart (Priority: P1)

The chart draws candles, the channel's centre and boundaries, the zones a
setup lives in, and a marker at the signal.

**Why this priority**: REQ-WP-009's first four acceptance criteria, and PRD
§27.2's overlay list.

**Independent Test**: Render with known data and assert each layer's presence
and position.

**Acceptance Scenarios**:

1. **Given** bars, **When** the chart renders, **Then** candles appear for each.
2. **Given** a channel snapshot, **When** the chart renders, **Then** centre, upper and lower lines appear.
3. **Given** a channel snapshot, **When** the chart renders, **Then** the upper, middle and lower zones appear as bands.
4. **Given** a signal, **When** the chart renders, **Then** a marker appears at its event time, on the boundary it concerns.
5. **Given** no channel for the selected instant, **When** the chart renders, **Then** candles appear and no channel is drawn — an absent channel is not a flat one.

---

### Edge Cases

- What happens when a deep link names a signal that does not exist? The chart loads the symbol and timeframe and says the signal was not found, rather than showing an empty page or a silently different instant.
- What happens when the requested range holds no bars? An empty series, and the chart says so. A blank chart with no explanation is indistinguishable from a broken one.
- What happens when `as_seen_then=false` is requested for an instant with too little history to fit a channel? The refit is refused with a stated reason, not approximated over fewer bars.
- What happens when the API is unreachable from the chart? The chart says the data could not be loaded and does not render a partial state that could be mistaken for real data.
- What happens when the WebSocket drops? The chart shows that it is no longer live. A stale chart that looks live is the same failure PRD §25.6 forbids for alerts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `GET /api/v1/channels` MUST default `as_seen_then` to true.
- **FR-002**: With `as_seen_then=true` the API MUST return the stored snapshot unmodified, never a refit.
- **FR-003**: With `as_seen_then=false` the API MUST return a channel fitted over history up to the requested instant, and MUST refuse rather than approximate when there is too little.
- **FR-004**: `GET /api/v1/bars` MUST filter by venue, symbol, timeframe and time range, and honour a limit by returning the most recent matches.
- **FR-005**: `GET /api/v1/markets` MUST filter by venue and market type.
- **FR-006**: `GET /api/v1/features/snapshot` and `/timeseries` MUST serve stored feature values for a venue, symbol, timeframe and instant or range.
- **FR-007**: `GET /api/v1/signals` MUST filter by symbol, timeframe, status and time range.
- **FR-008**: `GET /api/v1/signals/{id}` MUST return the decision, channel and feature snapshots, and MUST return any later outcome as a separate field.
- **FR-009**: A query matching nothing MUST return an empty result, not an error.
- **FR-010**: The API MUST NOT compute a channel, feature or signal itself beyond FR-003's explicit refit — it reads what the pipeline produced.
- **FR-011**: `/ws/market` MUST accept PRD §28.7's subscribe message and deliver only the named channels, for the named venue, symbol and timeframe.
- **FR-012**: A malformed subscribe message MUST be rejected with a stated reason without closing the connection.
- **FR-013**: The chart MUST render candles, the channel's centre and boundaries, the setup zones, and a marker at the signal.
- **FR-014**: The chart MUST open a deep link in `AS-SEEN-THEN` mode and MUST display which mode it is in.
- **FR-015**: The chart MUST distinguish "no data" from "not loaded" from "no longer live" on screen.
- **FR-016**: The chart MUST NOT render a partial or failed load as though it were data.
- **FR-017**: No API module may compute a value from data later than the instant requested.

### Key Entities

- **Repository**: whatever holds bars, snapshots, features and signals for the API to read.
- **Channel mode**: `AS-SEEN-THEN` or `CURRENT REFIT`, and which one a reader is looking at.
- **Subscription**: a venue, symbol, timeframe and set of channels.
- **Chart state**: what is loaded, what is live, and what is merely absent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A request omitting `as_seen_then` returns the stored snapshot.
- **SC-002**: For an instant with later history, the two modes return different channels, and the stored one is byte-identical to what was stored.
- **SC-003**: Each endpoint's filters return exactly the matching records, in event-time order.
- **SC-004**: An empty match returns an empty result with a success status.
- **SC-005**: A subscriber receives updates only for its named channels, venue, symbol and timeframe.
- **SC-006**: A malformed subscribe message leaves the connection usable.
- **SC-007**: The chart renders candles, channel lines, zones and a marker from known data.
- **SC-008**: A chart opened from a deep link is in `AS-SEEN-THEN` mode and says so.
- **SC-009**: A failed load renders as a stated failure, never as an empty chart.
- **SC-010**: No API module reads data later than the requested instant, verified by a test that plants later data and asserts it is not returned.

## Assumptions

- **No storage, so a repository port.** PRD §29's tables are unbuilt. The API depends on a protocol; an in-memory implementation serves it now and a durable one arrives with §29 without touching the endpoints.
- **`min_score` and `setup_type` filters are not implemented.** Both need PRD §43's ranker and a setup taxonomy that does not exist. They stay in REQ-API-001's text as what is owed.
- **The explanation's score breakdown and model probabilities are omitted**, for the reasons ADR-016 already records for the alert message.
- **§27.2's remaining overlays are out of scope**: volume profile (REQ-WP-012), DEX liquidity (REQ-WP-015), liquidation levels (REQ-WP-013), VWAP and POC. REQ-WP-009's acceptance names four layers and this builds those four.
- **§27.3's lower panes and §27.4's explanation panel are out of scope** for the same reason.
- No authentication. The API is not exposed publicly in this phase, and inventing an auth scheme the PRD does not specify would be worse than leaving the boundary explicit.
