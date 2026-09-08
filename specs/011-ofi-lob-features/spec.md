---
traces: [REQ-WP-011, REQ-PRIN-008]
status: draft
---

# Feature Specification: OFI / LOB features

**Feature Branch**: `wp-011-ofi-lob-features`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-011 — QI; depth imbalance; microprice; OFI; CVD; wall
persistence. REQ-PRIN-008 — every feature declares its semantics, unit,
cadence, source, freshness and leakage policy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read the pressure in a book at an instant (Priority: P1)

Given a valid book, a consumer gets queue imbalance at the touch, depth
imbalance over the top N levels and over fixed basis-point bands, the
microprice, and how far it sits from the mid.

**Why this priority**: PRD §15.1 and §15.2. These are pure functions of one
book state — no history, no windows — so they are the smallest thing that is
useful on its own, and everything stateful below is built from the same
readings.

**Independent Test**: Build a book with known levels and compare each value
against hand arithmetic.

**Acceptance Scenarios**:

1. **Given** a book with more resting size on the bid, **When** queue imbalance is read, **Then** it is positive, and it is `(bid - ask) / (bid + ask)` at the touch.
2. **Given** a book, **When** depth imbalance is read for the top 1, 5, 10, 20 and 50 levels, **Then** each is the same ratio over that many levels per side.
3. **Given** a book, **When** depth imbalance is read for the ±5, 10, 25 and 50 bps bands, **Then** each uses the distance-based depth of REQ-WP-004, measured from the mid.
4. **Given** a book whose ask queue is much larger than its bid queue, **When** the microprice is read, **Then** it sits below the mid — the larger queue pushes the price away from itself.
5. **Given** an invalid or un-bootstrapped book, **When** any of these is read, **Then** it refuses. PRD §11.1 rule 6.

---

### User Story 2 - Measure order flow imbalance over a window (Priority: P1)

Consecutive top-of-book observations produce an OFI increment each; increments
accumulate over event-time windows of 1s, 5s, 30s, 1m and one bar.

**Why this priority**: PRD §15.3 requires it by name, and PRD §19's own example
of a registered feature is `ofi_5s`. Equal to US1 because it is the feature the
work package is named for.

**Independent Test**: Feed a scripted sequence of book states whose Cont-style
increments are computed by hand, and compare the window totals.

**Acceptance Scenarios**:

1. **Given** two consecutive book states, **When** the increment is computed, **Then** it follows the Cont definition: a bid whose price rose contributes its new size, a bid whose price fell removes the old size, and symmetrically for the ask.
2. **Given** a bid price unchanged between observations, **When** the increment is computed, **Then** it contributes the *change* in bid size, not the size itself.
3. **Given** observations spanning more than one window, **When** a window's total is read, **Then** it includes exactly the increments whose event time falls inside it.
4. **Given** a window with no observations, **When** its total is read, **Then** it is zero and is marked as resting on no observations — an empty window and a balanced one are different facts.
5. **Given** a gap in the book, **When** observations resume after a rebuild, **Then** the increment across the gap is not computed: the two states are not consecutive, and differencing them would invent flow that was never observed.

---

### User Story 3 - Follow aggressive volume over time (Priority: P2)

Signed trade notional accumulates into cumulative volume delta, with its rate
of change, its acceleration, and delta normalized by total volume.

**Why this priority**: PRD §15.4. Below US1 and US2 because it reads the trade
stream rather than the book, so nothing else here depends on it.

**Independent Test**: Feed a scripted trade sequence and compare against hand
arithmetic.

**Acceptance Scenarios**:

1. **Given** a sequence of trades, **When** delta is read, **Then** it is aggressive buy notional minus aggressive sell notional.
2. **Given** a sequence of trades, **When** cumulative delta is read, **Then** it is the running sum of those deltas.
3. **Given** trades whose aggressor side is unknown, **When** delta is computed, **Then** they contribute to total volume but to neither side — an unknown side is not a zero-sized one.
4. **Given** a window of trades, **When** normalized delta is read, **Then** it is delta divided by total notional in that window, and a window with no volume has no value rather than a zero.

---

### User Story 4 - Watch a resting wall live and die (Priority: P2)

A level whose size is anomalous against its neighbours becomes a tracked wall.
Its lifetime, refills, and the split between what traded through it and what
was pulled are recorded.

**Why this priority**: PRD §15.6 and the last of REQ-WP-011's acceptance
criteria. P2 because it is the only part that needs both streams at once, and
because PRD §2.2 warns that resting size is the least trustworthy signal in the
book — a reason to build it carefully rather than first.

**Independent Test**: Script a wall that appears, refills, partially trades and
is then pulled, and check each field of its recorded state.

**Acceptance Scenarios**:

1. **Given** a level far larger than its neighbours, **When** the book is observed, **Then** a wall is tracked with its side, price band and first-seen event time.
2. **Given** a tracked wall whose size falls, **When** trades executed at that price in the same interval are known, **Then** the decrease is split into executed and cancelled, with executed never exceeding what actually traded there.
3. **Given** a tracked wall whose size rises again, **When** the book is observed, **Then** its refill count increases and it is not treated as a new wall.
4. **Given** a tracked wall that disappears, **When** the book is observed, **Then** its last-seen time and total persistence are final and are never rewritten.

---

### User Story 5 - Know what a number means before using it (Priority: P1)

Every feature this package exposes carries a registration: name, version,
family, description, formula, units, source events, lookback, cadence,
availability lag, null policy, clipping, normalization, point-in-time safety
and a test fixture.

**Why this priority**: PRD §19 opens with "Every feature definition must be
registered" and Constitution Principle VI ends "an undocumented feature is not
done". P1 because a registry added afterwards is a documentation exercise;
built alongside, it is a gate — and REQ-PRIN-008 has no other home.

**Independent Test**: Enumerate the features the package exposes and the
registry's entries, and assert the two sets are equal with no field left blank.

**Acceptance Scenarios**:

1. **Given** the package's features, **When** the registry is checked, **Then** every one has an entry and every required field is populated.
2. **Given** a new feature added without a registration, **When** the suite runs, **Then** it fails, naming the unregistered feature.
3. **Given** a registered feature, **When** its point-in-time safety is read, **Then** it states whether the value at time `t` uses only data with `event_time <= t`.

---

### Edge Cases

- What happens when a book side is empty? Queue imbalance and microprice refuse: there is no queue to compare and no opposite size to weight by.
- What happens when both queues are zero-sized? Queue imbalance refuses rather than dividing by zero. A book with two empty touches carries no imbalance information.
- What happens when a window is asked for before enough history exists? It answers from what it has and says how many observations that was, so a caller can tell a thin window from a full one.
- What happens when trades arrive out of event-time order? They are accepted only in order; an out-of-order trade is refused rather than silently rewriting a cumulative total that was already read.
- What happens when a wall's price band moves? It is a different wall. PRD §15.6 has `move_count`, so a wall that shifts price is recorded as having moved rather than as two unrelated walls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Queue imbalance MUST be `(bid_qty - ask_qty) / (bid_qty + ask_qty)` at the touch.
- **FR-002**: Depth imbalance MUST be computable over the top 1, 5, 10, 20 and 50 levels.
- **FR-003**: Depth imbalance MUST be computable over the ±5, 10, 25 and 50 bps bands, using REQ-WP-004's mid-referenced depth.
- **FR-004**: The microprice MUST weight each side's price by the *opposite* queue size, and its distance from the mid MUST be reported.
- **FR-005**: Every book feature MUST refuse when the book is invalid or has not bootstrapped.
- **FR-006**: OFI increments MUST follow the Cont definition over consecutive top-of-book observations.
- **FR-007**: OFI MUST accumulate over event-time windows of 1s, 5s, 30s, 1m and one bar.
- **FR-008**: An OFI window MUST report how many observations it rests on, so an empty window is distinguishable from a balanced one.
- **FR-009**: No OFI increment MUST be computed across a book gap or rebuild.
- **FR-010**: Delta MUST be aggressive buy notional minus aggressive sell notional; trades of unknown aggressor MUST count toward volume and toward neither side.
- **FR-011**: Cumulative volume delta MUST be the running sum of delta, with slope and acceleration over a window, and delta normalized by that window's total notional.
- **FR-012**: A window with no volume MUST report no normalized delta rather than zero.
- **FR-013**: Walls MUST be identified by anomalous size relative to neighbouring levels, with the threshold configurable.
- **FR-014**: A tracked wall MUST record side, price band, first seen, last seen, max size, average size, refill count, move count and persistence.
- **FR-015**: A wall's size decrease MUST be split into executed and cancelled, with executed bounded by the volume actually traded at that price.
- **FR-016**: A wall's finalized record MUST never be rewritten.
- **FR-017**: Every feature exposed by this package MUST carry a registry entry with all of PRD §19's required metadata.
- **FR-018**: A feature without a registry entry MUST fail the test suite by name.
- **FR-019**: No module in this package may consult a system clock. All time comes from event times.
- **FR-020**: Every feature MUST be computable from data with `event_time <= t`, and its registration MUST state so.

### Key Entities

- **Book reading**: the instantaneous quantities a book feature is computed from.
- **OFI window**: a span of event time, the increments inside it, and how many observations produced them.
- **Volume delta series**: signed notional over time and its running total.
- **Wall**: a price band on one side, and the history of what happened to the size resting there.
- **Feature registration**: what a number means, where it comes from, and whether it is safe to use at time `t`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every instant feature matches hand arithmetic on a constructed book.
- **SC-002**: The microprice moves away from the larger queue, and equals the mid when the queues are equal.
- **SC-003**: OFI over a scripted sequence equals the hand-computed Cont increments, summed per window.
- **SC-004**: No increment is produced across a gap, verified by driving a book through one.
- **SC-005**: Cumulative delta over a scripted trade sequence matches hand arithmetic, and unknown-aggressor trades change volume without changing delta.
- **SC-006**: A scripted wall's lifecycle — appear, refill, partially execute, pull — is recorded field by field, and executed never exceeds volume traded at that price.
- **SC-007**: The set of exposed features equals the set of registered features, with no required field blank.
- **SC-008**: No module in the package references a system clock, verified over the source.
- **SC-009**: Every feature refuses on an invalid or un-bootstrapped book.

## Assumptions

- **Scope is REQ-WP-011's acceptance list.** PRD §15.5's remaining shape features — cumulative-depth slope, convexity, depth concentration, gap to next significant liquidity — and §15.7's absorption are not in it and are not built here. The distance between §15 and this package is deliberate and visible.
- Features are computed in memory from live values. PRD §24.1's feature snapshot table and §29's storage are unbuilt, so nothing here is persisted.
- The wall detector's anomaly threshold is a research default, not a proven parameter — PRD §13.11's warning applies to it as much as to the zone bounds.
- Trades arrive normalized (REQ-WP-002's `TradeEvent`), and the book is REQ-WP-004's service.
- Bar-length OFI windows use REQ-WP-005's bar boundaries; this package does not define its own.
