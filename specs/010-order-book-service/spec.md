---
traces: [REQ-WP-004]
status: draft
---

# Feature Specification: Order book service

**Feature Branch**: `wp-004-order-book-service`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-004 — buffer + snapshot bootstrap; exact sequence validation;
rebuild on gap; top-N access; depth-at-bps query; health state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bootstrap a trustworthy book from a live stream (Priority: P1)

A feed starts mid-stream. Deltas arrive before any snapshot exists, so they are
buffered; a snapshot arrives; the deltas the snapshot already covers are
discarded and the rest are applied in exact sequence. The book is usable only
once that has happened.

**Why this priority**: PRD §11.1 states the procedure in five steps and it is
the whole of "buffer + snapshot bootstrap". Everything else in this feature
reads a book; this is what makes there be one to read.

**Independent Test**: Feed deltas, then a snapshot whose `update_id` falls in
the middle of them, and check the resulting book equals one built by applying
only the deltas after the snapshot.

**Acceptance Scenarios**:

1. **Given** deltas arriving before a snapshot, **When** the snapshot arrives, **Then** deltas it already covers are discarded and the remainder applied in order.
2. **Given** a book that has not yet bootstrapped, **When** it is queried, **Then** it refuses rather than answering from a partial state.
3. **Given** a buffered delta that does not connect to the snapshot, **When** bootstrap runs, **Then** the bootstrap fails and a new snapshot is requested — a book with a hole in it is never presented as bootstrapped.

---

### User Story 2 - Never answer from a book that has diverged (Priority: P1)

A sequence gap means the local book and the venue's book no longer agree. The
book records the gap, stops answering, and asks to be rebuilt.

**Why this priority**: Equal to US1. PRD §8.1 forbids hiding sequence gaps and
§11.1 rule 6 forbids emitting features from an invalid or stale book. A book
that answered anyway would be indistinguishable from a correct one downstream,
which is the failure this requirement exists to prevent.

**Independent Test**: Apply a delta that skips a sequence, then query. Every
query must refuse, and the health state must report the gap.

**Acceptance Scenarios**:

1. **Given** a delta whose first sequence does not follow the last applied one, **When** it is offered, **Then** it is refused, the gap is counted, and the book becomes invalid.
2. **Given** an invalid book, **When** any read is attempted, **Then** it refuses rather than returning its last good contents.
3. **Given** an invalid book, **When** a fresh snapshot is supplied, **Then** the book rebuilds from it and becomes valid again, and the gap count survives the rebuild.

---

### User Story 3 - Read the shape of the book (Priority: P2)

A consumer asks for the top N levels of each side, or for the quantity resting
within a given distance of the mid price.

**Why this priority**: Below US1 and US2 because a wrong answer is worse than no
answer — these reads are only meaningful once the book is known to be valid.
PRD §15.1 names the bands (±5/10/25/50 bps) and §15.5 asks for depth within X
bps; WP-011 consumes both.

**Independent Test**: Build a book with known levels, ask for the top 3 and for
depth at 10 bps, and compare against the totals computed by hand.

**Acceptance Scenarios**:

1. **Given** a valid book, **When** the top N levels are requested, **Then** bids come back descending by price and asks ascending, at most N of each.
2. **Given** a valid book, **When** depth within X bps is requested, **Then** the quantity resting within that distance of the mid price is returned per side.
3. **Given** a book with fewer than N levels on a side, **When** the top N is requested, **Then** what exists is returned rather than an error or padding.

---

### User Story 4 - See whether the book can be trusted (Priority: P2)

An operator reads the book's health: whether it is valid, how many gaps it has
seen, the last sequence applied, and how far behind the data it is.

**Why this priority**: PRD §11.1 requires the status structure. It is P2 rather
than P1 because the refusals in US2 already prevent bad data; health is what
makes the reason visible rather than mysterious.

**Independent Test**: Drive a book through bootstrap, a gap and a rebuild, and
check the health at each step.

**Acceptance Scenarios**:

1. **Given** a book at any point in its life, **When** its health is read, **Then** it reports validity, gap count, last sequence, and staleness measured in event time.
2. **Given** a book whose most recent applied event is older than the time being asked about, **When** health is read, **Then** the staleness is the difference between those two event times — not a wall-clock reading.

---

### Edge Cases

- What happens when a delta arrives with no sequence range at all? It is refused. A delta whose position in the sequence is unknown cannot be validated, and applying it would silently break the guarantee the whole feature rests on.
- What happens when a snapshot older than the book arrives? It is ignored: rebuilding backwards would discard known-good state in favour of staler state.
- What happens when a rebuild snapshot itself does not connect to the buffered deltas? The bootstrap fails and another snapshot is requested. The book stays invalid meanwhile.
- What happens when depth is asked of an empty side? Zero — an empty side has no resting quantity, which is a fact, not an error.
- What happens when the mid price cannot be computed because one side is empty? Depth-at-bps refuses. There is no reference price, so the answer would be arbitrary.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST buffer deltas that arrive before a snapshot and apply them after it, in sequence order.
- **FR-002**: The service MUST discard buffered deltas the snapshot already covers.
- **FR-003**: The service MUST validate that each applied delta continues the sequence exactly, and refuse any that does not.
- **FR-004**: A refused delta MUST increment a gap count and mark the book invalid.
- **FR-005**: An invalid book MUST refuse every read — top-N, depth, and best bid/ask alike.
- **FR-006**: The service MUST rebuild from a fresh snapshot on request, becoming valid again, while retaining its cumulative gap count.
- **FR-007**: The service MUST report the top N levels per side, bids descending and asks ascending by price.
- **FR-008**: The service MUST report resting quantity per side within a given distance in basis points of the mid price.
- **FR-009**: The service MUST report health: validity, gap count, last applied sequence, and staleness.
- **FR-010**: Staleness MUST be measured between event times supplied by the caller. No module in this feature may consult a system clock.
- **FR-011**: The service MUST be venue-agnostic: it takes normalized deltas and snapshots, and contains no exchange-specific parsing.
- **FR-012**: The service MUST NOT perform I/O. A rebuild is requested by the service and supplied by its caller.
- **FR-013**: A book that has not bootstrapped MUST refuse every read.

### Key Entities

- **Book state**: the resting quantity at each price on each side, plus the sequence position that state corresponds to.
- **Book health**: whether the state can be trusted, and the history that determines it.
- **Bootstrap buffer**: deltas held until a snapshot gives them a starting point.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A book bootstrapped from buffered deltas plus a mid-stream snapshot is identical to one built by applying only the deltas after that snapshot.
- **SC-002**: Every delta that breaks the sequence is refused, and no refused delta changes the book's contents.
- **SC-003**: After a gap, every read refuses until a rebuild; after the rebuild, reads succeed and the gap count still shows the gap.
- **SC-004**: Top-N and depth-at-bps answers match hand-computed values on a constructed book.
- **SC-005**: Health reports validity, gap count, last sequence and staleness at every stage of the lifecycle.
- **SC-006**: No module in the feature references a system clock, verified over the source.
- **SC-007**: Two identical delta streams produce identical books and identical health.

## Assumptions

- Snapshot-and-delta semantics, as PRD §11.1 describes. Venues that stream a full book each tick are out of scope until one is added.
- One book per venue and symbol. Cross-venue consolidation is REQ-WP-016.
- Deltas and snapshots arrive already normalized (REQ-WP-002's `BookDelta` and `BookSnapshot`). Fetching them is the connector's job.
- No persistence. The book is in-memory state; PRD §29.4's `market.book_snapshot.v1` table is a later concern.
- The features of PRD §15 — queue imbalance, microprice, OFI, book shape — are REQ-WP-011 and are not built here. This feature supplies the book those features read.
