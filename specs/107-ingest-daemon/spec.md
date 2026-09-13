---
traces: [REQ-WP-066]
status: draft
---

# Feature Specification: The ingest daemon

**Feature Branch**: `wp-066-ingest-daemon`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-066 — PRD §6.2's `ingest-binance`, and §6.4.4's raw zone.

## Context

REQ-PIPE-001 deferred a live process deliberately. It is wanted now, because a
stack nobody can feed shows nothing. Everything that decides already exists and
is tested — `StreamSession`, `normalize`, `BarBuilder`, `BarSink` — so this is
the loop that turns them into a process, arranged so the untestable part is the
only part with no decisions in it.

Measured on the venue, 2026-09-13: Binance sends a protocol PING every 20
seconds and drops a client that does not answer; `websockets` answers from the
connection's own task. One symbol on two streams is 800 frames a minute, 556 MiB
a day raw, 12.3% of that compressed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Containers up, data on the chart (Priority: P1)

**Acceptance**: `docker compose up` starts the daemon; within two minutes the
API serves bars for the configured symbol and the chart route returns them.

### User Story 2 - Every frame is kept (Priority: P1)

**Acceptance**: one compressed object per minute under §6.4.4's raw zone, and a
frame comes back byte-identical.

### User Story 3 - A bad frame does not stop the ingest (Priority: P1)

**Acceptance**: unreadable and unnormalisable frames are counted, archived, and
the step continues.

### User Story 4 - CI runs the daemon, not a rehearsal (Priority: P1)

**Acceptance**: the same daemon runs behind `ReplayTransport` over recorded
frames.

### Edge Cases

- Heavy work on the socket's event loop stops the pongs and the venue drops us,
  with no error.
- `BTCUSDT@aggTrade` connects and delivers nothing; `btcusdt@aggTrade` delivers.
- A quiet minute must write no object.
- A buffer kept after a write repeats frames in the next object.
- Closing before committing turns a shutdown into an apparent data gap.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The socket runs in its own thread; frames cross by queue.
- **FR-002**: `pong` is a no-op and says why.
- **FR-003**: Frames are archived before anything is decided about them.
- **FR-004**: One compressed object per minute, keyed by UTC date.
- **FR-005**: Unparsed and ignored frames are counted, never dropped silently.
- **FR-006**: `step()` holds the behaviour; `run()` only decides when to call it.
- **FR-007**: `stop()` commits, then closes.
- **FR-008**: Stream names are lower-cased.
- **FR-009**: Configuration refuses a missing symbol list or archive URI.
- **FR-010**: One process per symbol.

### Key Entities

- **WebsocketTransport / ReplayTransport** — one seam, two implementations.
- **FrameArchive / ObjectStore** — the raw tier and where it goes.
- **IngestDaemon / StepReport** — the loop and what one step did.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Run against the live venue: 76 frames, 76 trades, 4 bars, 2
  archive objects in 20 seconds.
- **SC-002**: The API serves those bars through nginx.
- **SC-003**: A frame survives the archive round trip byte for byte.
- **SC-004**: Mutating the archive-first rule, the counters, the shutdown order
  or the stream casing is caught by a test.

## Assumptions

- Bars need trades, so only `@aggTrade` is consumed; depth is archived and
  counted as ignored until a book is maintained.

## Open Questions

- A live daemon gives one candle per timeframe; seeding history is separate, and
  `Bar` refuses a venue kline because it requires fields a kline does not carry.
