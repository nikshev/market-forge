---
traces: [REQ-WP-012]
status: draft
---

# Feature Specification: Volume profile

**Feature Branch**: `wp-012-volume-profile`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-012 — trade-level bins; POC/VAH/VAL; HVN/LVN; chart plugin.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the profile from trades, not from candles (Priority: P1)

Volume is binned by the price it actually traded at, taken from the trade
stream.

**Why this priority**: PRD §14.1 opens with it — "Compute true trade-based
volume by price bins from exchange trades where available" — and adds the
prohibition that gives it teeth: "Do not infer buy/sell direction from candle
color if aggressor-side trades are available." A profile built from candles is
a different, worse measurement wearing the same name.

**Independent Test**: Trades at known prices and sizes, and a profile compared
against hand-summed bins.

**Acceptance Scenarios**:

1. **Given** trades at several prices, **When** the profile is built, **Then** each bin holds the volume that traded inside it.
2. **Given** aggressor sides on the trades, **When** the profile is built, **Then** buy and sell volume are separated from the sides, never inferred.
3. **Given** trades with unknown aggressor, **When** the profile is built, **Then** they count in total volume and in neither side.
4. **Given** a bin width, **When** the profile is built, **Then** bins are contiguous and a trade falls in exactly one.

---

### User Story 2 - Find where the market agreed (Priority: P1)

The point of control, and the value area around it holding a configurable share
of the volume.

**Why this priority**: PRD §14.1's first three outputs. Everything else in the
family is measured relative to them.

**Acceptance Scenarios**:

1. **Given** a profile, **When** the POC is read, **Then** it is the bin holding the most volume.
2. **Given** a value-area percentage, **When** the value area is read, **Then** it is a contiguous run of bins containing at least that share.
3. **Given** a value area, **When** its bounds are read, **Then** VAH is its highest price and VAL its lowest.
4. **Given** two bins tied for most volume, **When** the POC is read, **Then** the tie is broken by the rule the profile states, and stated in the result.
5. **Given** an empty profile, **When** the POC is requested, **Then** it refuses.

---

### User Story 3 - Find the shelves and the gaps (Priority: P2)

High-volume nodes where price spent effort, and low-volume nodes it moved
through quickly.

**Why this priority**: PRD §14.1's HVN and LVN outputs. P2 because they are
derived from a profile that must be right first.

**Acceptance Scenarios**:

1. **Given** a bin far above its neighbours, **When** nodes are read, **Then** it is a high-volume node.
2. **Given** a bin far below its neighbours, **When** nodes are read, **Then** it is a low-volume node.
3. **Given** a uniform profile, **When** nodes are read, **Then** there are none — a flat profile has no structure to report.
4. **Given** a channel's boundaries, **When** overlap is read, **Then** it names the nodes the boundaries fall inside.

---

### User Story 4 - Read the profile's shape (Priority: P2)

Entropy, skew, and distances from the current price to the POC and the value
area edges.

**Why this priority**: PRD §14.1's remaining outputs, and the ones a signal
would consume.

**Acceptance Scenarios**:

1. **Given** a concentrated profile, **When** entropy is read, **Then** it is lower than for a dispersed one.
2. **Given** a profile with more volume above the POC, **When** skew is read, **Then** it is positive.
3. **Given** a price, **When** distances are read, **Then** they are in basis points relative to the price.

---

### User Story 5 - See the profile on the chart (Priority: P2)

The chart draws the profile beside the candles, with the POC and value area
marked.

**Why this priority**: REQ-WP-012's fourth acceptance criterion, and PRD
§27.2's overlay list.

**Acceptance Scenarios**:

1. **Given** a profile, **When** the chart renders, **Then** each bin appears as a horizontal bar proportional to its volume.
2. **Given** a profile, **When** the chart renders, **Then** the POC and the value-area bounds are distinguishable from ordinary bins.
3. **Given** no profile, **When** the chart renders, **Then** the candles appear and no profile is drawn.

---

### Edge Cases

- What happens when every trade is at one price? One bin, which is the POC, and the value area is that bin. Entropy is zero, which is correct rather than degenerate.
- What happens when the value-area percentage cannot be reached without taking every bin? The whole profile is the value area, and the result says the target was not met by a proper subset.
- What happens when a trade's price sits exactly on a bin boundary? It falls in the upper bin, consistently, so the same trades always give the same profile.
- What happens when the profile window contains no trades? Building refuses rather than returning an empty profile whose POC would then have to be invented.
- What happens when two bins tie for most volume? The lower price wins, and the profile records that the tie occurred.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Volume MUST be binned from trade prices, never inferred from bar direction.
- **FR-002**: Buy and sell volume MUST come from the trade's aggressor side; unknown-aggressor trades MUST count in total and in neither side.
- **FR-003**: Bins MUST be contiguous and a trade MUST fall in exactly one, with boundary trades resolved consistently.
- **FR-004**: The POC MUST be the highest-volume bin, with ties broken by the lower price and the tie recorded.
- **FR-005**: The value area MUST be a contiguous run of bins around the POC holding at least the configured share, default 70%.
- **FR-006**: VAH and VAL MUST be the value area's highest and lowest prices.
- **FR-007**: Building a profile from no trades MUST refuse.
- **FR-008**: High- and low-volume nodes MUST be identified relative to neighbouring bins, with the threshold configurable.
- **FR-009**: A uniform profile MUST report no nodes.
- **FR-010**: The profile MUST report entropy, skew, and distances to the POC, VAH and VAL in basis points.
- **FR-011**: The profile MUST report which nodes a supplied channel's boundaries fall inside.
- **FR-012**: The chart MUST render bins proportionally and distinguish the POC and value-area bounds.
- **FR-013**: Every feature exposed MUST be registered.
- **FR-014**: No module may consult a system clock; all windows are event-time.

### Key Entities

- **Bin**: a price range and the volume that traded in it.
- **Profile**: the bins for a window, and what they say about where value was.
- **Node**: a bin that stands out from its neighbours, in either direction.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Bin volumes match hand-summed trades.
- **SC-002**: Buy and sell splits match the trades' own aggressor sides.
- **SC-003**: POC, VAH and VAL match hand-computed values on a constructed profile.
- **SC-004**: The value area holds at least the configured share and is contiguous.
- **SC-005**: A uniform profile yields no nodes; a shelved one yields the expected node.
- **SC-006**: Entropy is lower for a concentrated profile than a dispersed one.
- **SC-007**: An empty window refuses.
- **SC-008**: The chart's bar lengths are proportional to bin volume, and the POC is marked.
- **SC-009**: Exposed and registered feature sets are equal.

## Assumptions

- **PRD §14.2's VWAP family and §14.3's volume anomaly are not in scope.** Neither is named in REQ-WP-012's acceptance criteria. §14.3's z-scores would reuse REQ-WP-013's helper when they arrive.
- **Profile windows are supplied by the caller.** §14.1 lists rolling 4h/24h/7d and anchored session profiles; the builder takes a trade list and a window, so all of those are the caller choosing what to pass. The anchoring rules themselves are not built.
- **No storage.** Profiles are computed from trades in memory.
