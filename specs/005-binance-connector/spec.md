---
traces: [REQ-WP-003]
status: draft
---

# Feature Specification: Binance connector

**Feature Branch**: `005-binance-connector`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-003 — reconnect before/at 24h lifecycle; ping/pong compliance; combined streams configurable; trades; book deltas; mark/funding; OI polling; liquidations when available; error metrics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn venue messages into canonical events (Priority: P1)

A recorded Binance message becomes a canonical event with the right values in
the right fields — and above all, with the venue's clock and our clock kept
apart.

**Why this priority**: Everything else in the connector is transport. If a
message is normalized wrongly, every downstream guarantee about ordering and
non-repainting is built on a mistake. PRD §0.3 and §0.4 make this the one thing
that cannot be got wrong.

**Independent Test**: Replay the committed fixtures through the normalizer and
compare against expected canonical events. No network, no services.

**Acceptance Scenarios**:

1. **Given** a recorded aggregate-trade message, **When** it is normalized, **Then** the result is a `TradeEvent` whose `event_time_ns` came from the venue's trade time and whose `ingest_time_ns` came from our receipt, and the two are distinguishable.
2. **Given** a venue millisecond timestamp, **When** it is normalized, **Then** it becomes nanoseconds exactly, with no rounding.
3. **Given** a message with a field the connector does not recognize, **When** it is normalized, **Then** it fails loudly rather than silently dropping it.
4. **Given** a malformed message, **When** it is normalized, **Then** it raises and the error identifies what was wrong.

---

### User Story 2 - Keep a correct order book, or admit it is broken (Priority: P1)

The connector maintains a local book from a REST snapshot plus a websocket delta
stream, following PRD §11.1's procedure exactly. When the sequence breaks, it
says so rather than serving a book that quietly diverged from the venue's.

**Why this priority**: Equal to US1. PRD §11.1 rule 6 forbids emitting features
from an invalid or stale book, and §8.1 forbids hiding sequence gaps. A book
that is wrong and says it is fine is worse than no book.

**Independent Test**: Replay the recorded snapshot and 30 consecutive deltas;
the book stays valid. Remove one delta to create a gap; the book reports itself
stale.

**Acceptance Scenarios**:

1. **Given** a REST snapshot and deltas buffered before it, **When** the book is built, **Then** deltas older than the snapshot are discarded and the rest applied in order.
2. **Given** a continuous delta sequence, **When** all are applied, **Then** the book reports valid with a gap count of zero.
3. **Given** a sequence with one delta missing, **When** the gap is reached, **Then** the book reports invalid, increments its gap count, and does not apply the out-of-order delta.
4. **Given** an invalid book, **When** anything asks it for state usable in features, **Then** it refuses rather than returning stale contents.
5. **Given** a delta level with zero quantity, **When** it is applied, **Then** that price level is removed from the book.

---

### User Story 3 - Stay connected across the venue's limits (Priority: P2)

The connector survives a 24-hour stream lifetime and the venue's keepalive rules
without a human restarting it, and reports what went wrong when something does.

**Why this priority**: Below US1 and US2 because a connector that disconnects
loses data visibly, while one that normalizes wrongly corrupts data invisibly.
Still required: PRD §36 expects continuous operation.

**Independent Test**: Drive the lifecycle logic with a fake clock and a fake
transport; no socket is opened.

**Acceptance Scenarios**:

1. **Given** a connection approaching the venue's 24-hour limit, **When** the threshold is reached, **Then** the connector reconnects before the venue closes it.
2. **Given** a ping frame from the venue, **When** it arrives, **Then** the connector responds within the venue's deadline.
3. **Given** a dropped connection, **When** the connector reconnects, **Then** it rebuilds the book from a fresh snapshot rather than resuming a stale one.
4. **Given** any failure, **When** it occurs, **Then** a counter for that failure kind increases and is readable.

---

### Edge Cases

- What happens when a delta arrives whose sequence precedes the snapshot? Discarded — PRD §11.1 step 3.
- What happens when the same message is delivered twice? The event's identity is unchanged, so a consumer can deduplicate — PRD §11.2.
- What happens when the venue's message shape changes? Normalization fails loudly; a silently ignored field is how a connector passes tests and reports wrong prices.
- What happens when a price arrives as a string with more digits than a double holds? It becomes an exact decimal — the venue sends strings for exactly this reason.
- What happens when the venue is unreachable at startup? The connector reports it and retries; it does not present an empty book as a valid one.
- What happens to the venue's own push timestamp, distinct from both trade time and our receipt time? See Assumptions — it is currently discarded, and that is a decision rather than an oversight.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The connector MUST normalize Binance aggregate-trade and trade messages into `TradeEvent`.
- **FR-002**: The connector MUST normalize Binance depth-update messages into `BookDelta`, and depth snapshots into `BookSnapshot`.
- **FR-003**: The connector MUST derive `DerivativesState` from the venue's mark-price, funding and open-interest data.
- **FR-004**: Normalization MUST set `event_time_ns` from the venue's own timestamp and `ingest_time_ns` from local receipt, and MUST NOT use one where the other is meant.
- **FR-005**: Millisecond venue timestamps MUST convert to nanoseconds exactly.
- **FR-006**: Prices and quantities MUST be parsed as exact decimals, never through a float.
- **FR-007**: A message that cannot be normalized MUST raise, naming what failed. Unknown fields MUST NOT be silently discarded.
- **FR-008**: The connector MUST reconstruct a local order book following PRD §11.1: buffer deltas, fetch snapshot, discard obsolete deltas, apply by exact sequence rules, mark stale on gap.
- **FR-009**: The book MUST expose the health state PRD §11.1 requires: validity, gap count, last sequence, and staleness.
- **FR-010**: An invalid or stale book MUST refuse to provide state for feature computation.
- **FR-011**: A delta level with zero quantity MUST remove that price level.
- **FR-012**: The connector MUST reconnect before the venue's 24-hour stream lifetime expires.
- **FR-013**: The connector MUST comply with the venue's ping/pong keepalive.
- **FR-014**: After any reconnection, the book MUST be rebuilt from a fresh snapshot.
- **FR-015**: The set of subscribed streams MUST be configurable, not hard-coded.
- **FR-016**: Open interest and funding MUST be obtained by polling, at a configurable interval.
- **FR-017**: The connector MUST expose counters for failure kinds: connection failures, sequence gaps, normalization failures, and poll failures.
- **FR-018**: Connector tests MUST replay committed fixtures and MUST NOT open a network connection.

### Key Entities

- **Normalizer**: turns one venue message into one canonical event. Pure, with no I/O, so it is testable against recorded bytes.
- **Order book**: the local reconstruction, plus its own honest account of whether it can be trusted.
- **Stream session**: the lifecycle around a connection — subscribing, keepalive, reconnecting, and counting what went wrong.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every committed fixture message normalizes into a canonical event, verified field by field against expected values.
- **SC-002**: A venue millisecond timestamp of 1788838909800 becomes exactly 1788838909800000000 nanoseconds.
- **SC-003**: `event_time_ns` and `ingest_time_ns` differ on every normalized event, and neither is derived from the other.
- **SC-004**: Replaying the recorded snapshot and its 30 consecutive deltas leaves the book valid with zero gaps.
- **SC-005**: Removing one delta from that sequence makes the book report invalid and raise its gap count, and it does not apply the out-of-order delta.
- **SC-006**: An invalid book refuses to supply state for feature computation.
- **SC-007**: The lifecycle reconnects before 24 hours, driven by a fake clock, with no socket opened.
- **SC-008**: The whole connector test suite runs with no network access.

## Assumptions

- **The venue's push timestamp is discarded, for now.** A Binance trade carries both a trade time and an event-push time, and we add a third when we receive it — three clocks for `EventMeta`'s two fields. `event_time_ns` takes the trade time, because that is when the venue says the thing happened; `ingest_time_ns` takes our receipt. The push time is dropped. It measures venue-side latency, no requirement needs that yet, and adding a field to a model ADR-003 has just fixed would be speculative. The raw value survives in the committed fixtures, so the decision is reversible without re-recording.
- **Liquidations are specified but cannot be verified here.** REQ-WP-003 asks for them "when available from the venue". Probing found the futures `@forceOrder` stream connects and stays silent from this network, as do futures `@aggTrade` and `@markPrice`, while futures `@depth` and all spot streams deliver normally. No liquidation fixture exists, so FR-003 covers mark price, funding and open interest via REST, and liquidation normalization is out of this feature's scope rather than claimed and untested.
- Rate limiting is not implemented. PRD §35.6 lists it among connector concerns, but polling intervals here are configuration, and no requirement yet states a limit to respect.
- The transport is separated from the logic so that normalization and book reconstruction are pure and testable against fixtures. That separation is the reason SC-008 is achievable.
- Spot and futures share one normalizer where their message shapes agree, which the recorded fixtures show they do for depth and trades.
