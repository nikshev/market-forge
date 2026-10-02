---
traces: [REQ-WP-078]
status: draft
---

# Feature Specification: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded

**Feature Branch**: `123-ingest-resilience`

**Created**: 2026-10-02

**Status**: Draft

**Input**: [[REQ-WP-078]] — PRD §6.2 (one ingest service per venue), §6.4.4 (the raw
zone's layout), §32 and §33 (what a feed owes the rest of the system), §35.6
(reconnect among what connector tests cover).

## Context

[[REQ-WP-076]] put three venues on the compose file and was marked implemented
with a green suite. Six days later, measured on the running deployment on
2026-10-02: one venue in three was delivering, one had been silent for four days
while its container reported `Up`, and one had never delivered a frame at all.
Every defect below was found by looking at the running system, and every one of
them had a passing test beside it.

That is the thing this specification is about, and it shapes how it is written.
**The tests passed because they tested the pieces, and the faults were in the
seams between them.** The archive-prefix test builds `FrameArchive` with its
default prefix, so it cannot see that `build_daemon` hands it a different one.
The reconnect tests drive a `StreamSession` with a fake connector, so they cannot
see that the real connectors' reader threads end without telling it. Each
requirement here is therefore stated at the seam, and an acceptance scenario
that could pass against the broken wiring is not an acceptance scenario.

### Seven defects, one cause

| # | defect | seam where it hides |
|---|---|---|
| 1 | OKX connects to a URL that answers 404, then subscribes with an instrument id the venue does not recognise | connector ↔ the venue |
| 2 | A connection that ends is not reopened for two venues of three | reader thread ↔ session |
| 3 | The silence limit is computed from a field that means something else for Binance | policy ↔ daemon |
| 4 | Archive objects are filed at the bucket root, venue twice | daemon wiring ↔ archive |
| 5 | The archive key has no symbol, so three processes overwrite each other | archive ↔ deployment topology |
| 6 | INFO on every trade, frame and step; no log cap | code ↔ operations |
| 7 | A failed open and a rejected subscription say nothing | connector ↔ the operator |

Defects 1 and 7 are two views of one fault: a thread that ends without a word
cannot be told from a quiet market, which this repository has recorded more than
once and decided against each time.

### What this does not touch

New Prometheus metrics are out of scope. §33 lists "reconnects" and "stale feed
count"; `docs/deployment.md` already records that nine of §33's eleven metrics
have no producer ([[REQ-WP-055]]), and giving two more a producer without a
dashboard to say so would repeat that. Here they are **log events with a stated
reason**. The DNS fault and the hard-coded container addresses were repaired in
`1cf4edb` and are not part of this.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every configured venue delivers (Priority: P1)

An operator brings the stack up and every ingest service — Binance, Bybit, OKX —
produces bars. Today OKX never does, and says nothing about why.

**Why this priority**: a venue that delivers nothing is a venue that is not in
the product, and OKX is one of the three §5.2 names.

**Independent Test**: start the OKX daemon against the live venue and read back
the `bars` table. Delivers the whole of its value on its own.

**Acceptance Scenarios**:

1. **Given** the OKX daemon configured for `BTC-USDT-SWAP`, **When** it starts,
   **Then** it connects to OKX's v5 public WebSocket endpoint and subscribes with
   the instrument exactly as OKX names it, and trade frames arrive.
2. **Given** a connector **built** by the daemon's own wiring, **When** its
   endpoint and subscription message are read back, **Then** they are OKX's — the
   test inspects what the wiring produced, not what a helper function returns when
   called with convenient arguments.
3. **Given** a venue that answers an open or a subscription with a refusal,
   **When** that happens, **Then** a WARNING is logged naming the venue and
   quoting the venue's own message, so the cause is readable without a debugger.

---

### User Story 2 - A dead feed comes back (Priority: P1)

A venue's socket dies — closed with a frame, closed without one, or simply gone
quiet — and the daemon reopens it. Today that holds for one venue in three.

**Why this priority**: the failure it prevents is invisible and indefinite. A
Binance daemon was `Up` for four days with no feed and no alert.

**Independent Test**: a connector whose reader ends **without** a close frame,
on a venue whose policy says it announces close. Today's shape for Binance and
OKX, and the one the session ignores.

**Acceptance Scenarios**:

1. **Given** a connector whose reader has ended, **When** the session next
   advances, **Then** it reconnects, regardless of whether the venue announces
   close.
2. **Given** a feed that has delivered nothing for longer than that venue's
   silence limit, **When** the session next advances, **Then** it reconnects, and
   the log says so once on entry to the condition and once on recovery — not on
   every step in between.
3. **Given** Binance, **When** a fake clock is advanced past 24 hours, **Then**
   the session reconnects: the venue closes a stream at that age, and the policy
   that says so must be the one in force.
4. **Given** a venue that refuses every connection, **When** the session keeps
   trying, **Then** attempts are never closer together than that venue's minimum
   connect interval, and the log does not grow by a line per attempt without
   bound.

---

### User Story 3 - The raw archive is where a reader looks, and keeps every symbol (Priority: P1)

Frames are archived under the zone §6.4.4 names, one object per minute **per
symbol**, so three processes on one venue stop overwriting each other.

**Why this priority**: the archive is the tier §7 calls the source of truth
"where re-normalization may be required", and what is overwritten there cannot
be recovered. Every minute this stays wrong loses more.

**Independent Test**: two archives for different symbols of one venue, flushed in
the same minute, then read back.

**Acceptance Scenarios**:

1. **Given** a daemon built through the deployment's own wiring with its own
   `CHANNELFLOW_ARCHIVE_URI`, **When** a frame is archived, **Then** the object
   key has the venue **once**, sits under `raw/cex/`, and names the symbol.
2. **Given** two symbols of one venue flushed in the same minute, **When** the
   objects are read back, **Then** there are **two**, and each holds only its own
   symbol's frames. Proven by reading the frames, not by comparing key strings —
   the earlier mistake looked correct as a string.
3. **Given** objects already written under the old keys, **When** they are
   migrated, **Then** each is placed under the new layout by the symbol its own
   frames name, verified by size and checksum, and only then removed from the old
   location.
4. **Given** an object holding frames of more than one symbol, **When** migration
   meets it, **Then** it is refused and left where it is.

---

### User Story 4 - One definition of what a venue expects (Priority: P2)

A venue's policy — keepalive, idle timeout, stream lifetime, silence limit — is
defined once. Today two registries define it with different numbers, and the
live daemon reads the one with the mistake.

**Why this priority**: it is the root of defect 3, and it will cause the next
one. Not P1 because correcting the values (Story 2) is what restores behaviour;
this is what stops it drifting again.

**Independent Test**: define one venue's policy in two places with different
values and watch the suite fail.

**Acceptance Scenarios**:

1. **Given** the registries, **When** the suite runs, **Then** it fails if a
   venue's policy is defined in two places with different values.
2. **Given** a policy, **When** it is read, **Then** the silence limit is its own
   field, with a stated basis, and is configurable (Principle X).

---

### User Story 5 - The log is bounded (Priority: P2)

An ingest service's log grows by events, not by traffic. Today it grows by
traffic: 6.6 GB from one service in six days.

**Why this priority**: not a correctness fault, but a disk-fill on a host that
runs other things, and it buries the one line that matters under millions that
don't.

**Independent Test**: run a daemon over a recorded segment and measure the bytes
it logs at INFO; read the compose file for a cap on every service.

**Acceptance Scenarios**:

1. **Given** the per-trade, per-frame and per-step path, **When** it runs at the
   default level, **Then** it logs nothing at INFO.
2. **Given** a condition that persists, **When** it persists, **Then** its line
   is written on entry and on exit, not repeated.
3. **Given** the compose file, **When** a test reads it, **Then** every service
   carries a log size cap, and a service without one fails the test.
4. **Given** the log volume before and after, **When** the change is recorded,
   **Then** bytes per minute for each ingest service appear in the outcome note.

---

### Edge Cases

- **A venue that rejects every attempt** (banned address, bad configuration)
  must not be retried faster than its minimum connect interval, and must not
  turn its refusals into a line per attempt forever. The first is bounded by the
  policy; the second is bounded by logging the failure once and the recovery with
  a count.
- **A reconnect in the middle of a minute** must not lose what the daemon already
  holds: the bars builder and the archive buffer outlive the socket, and the gap
  is logged as a gap.
- **A process restart in the middle of a minute** still replaces that minute's
  object with the tail written after the restart, because the record of what was
  already written lives in memory. [[REQ-NRT-PARITY]] fixed this within one
  process; across a restart it remains, and this requirement does not claim
  otherwise.
- **Symbols that are not alike.** Binance and Bybit say `BTCUSDT`; OKX says
  `BTC-USDT-SWAP`. The archive path component is the configured symbol as
  written, not a normalised one, so two spellings of one instrument cannot split
  an archive and one spelling cannot merge two.
- **Migration interrupted halfway** must lose nothing: each object is copied,
  verified, then removed, so the worst state is a duplicate, never a gap, and
  running it again converges.
- **An old object with zero frames, or a frame whose stream names no symbol.**
  Refused and left in place, with the reason, for the same reason a
  multi-symbol object is.
- **Objects from before 2026-09-17** hold one symbol — BTCUSDT ran alone — and
  migrate like any other.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The OKX connector MUST open OKX's v5 public WebSocket endpoint and
  subscribe with the instrument as OKX names it, with no stream-name prefix.
- **FR-002**: A test MUST read the endpoint and subscription message from a
  connector **constructed by the daemon's wiring**, not from a helper called with
  chosen arguments.
- **FR-003**: A failed open, a rejected subscription, and an error event from a
  venue MUST each be logged at WARNING with the venue and the venue's own
  message. A reader thread MUST NOT end without a log line stating why.
- **FR-004**: The session MUST reconnect when its connector's reader has ended,
  for every venue, whatever the cause and whether or not the venue announces
  close.
- **FR-005**: A venue's policy MUST carry a maximum silence that is distinct from
  its idle timeout. It MUST be configurable, with a default per venue and a stated
  basis for each.
- **FR-006**: A feed silent beyond its maximum silence MUST be reconnected. The
  condition MUST be logged once on entry and once on recovery.
- **FR-007**: Binance's policy MUST carry its 24-hour stream lifetime, and the
  session MUST reconnect when it elapses.
- **FR-008**: Reconnect attempts MUST respect each venue's minimum connect
  interval and MUST NOT produce an unbounded number of log lines when a venue
  refuses every attempt.
- **FR-009**: Each venue's policy MUST be defined in exactly one place, and the
  suite MUST fail if two definitions of one venue disagree.
- **FR-010**: Archive object keys MUST contain the venue exactly once, lie under
  `raw/cex/`, and contain the symbol.
- **FR-011**: A test MUST derive the archive key through the daemon's wiring with
  the deployment's own archive URI, so a mistake in how the wiring builds the
  prefix is reachable by it.
- **FR-012**: Two symbols of one venue archived in the same minute MUST produce
  two objects, each containing only its own symbol's frames, proven by reading
  frames back.
- **FR-013**: Objects already written MUST be migrated to the new layout by the
  symbol their frames name, verified by size and checksum before the original is
  removed. An object that cannot be attributed to exactly one symbol MUST be
  refused and left in place, with the reason.
- **FR-014**: The extent of what was overwritten between 2026-09-17 and
  2026-09-26 MUST be recorded per symbol, as a count.
- **FR-015**: Nothing on the per-trade, per-frame or per-step path MAY log at
  INFO. A persisting condition MUST NOT repeat its line.
- **FR-016**: Every service in `docker-compose.yml` MUST carry a log size cap, and
  a test MUST read the file and fail for a service without one.
- **FR-017**: Log bytes per minute for each ingest service, before and after,
  MUST be recorded in the implement outcome note.

### Key Entities

- **Venue policy**: what one venue expects of a client and what this system
  expects of that venue — keepalive, idle timeout, stream lifetime, maximum
  silence, minimum connect interval. One definition per venue.
- **Connection**: a socket plus the reader that drains it. It is *alive* or it is
  not, and the session is entitled to ask.
- **Archive object**: one minute of one symbol's raw frames on one venue,
  identified by venue, symbol and minute.
- **Silence**: the interval since a feed last delivered a frame, judged against
  the venue's own maximum.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fresh start, every configured venue produces at least one
  committed bar within fifteen minutes (one flush interval), observed in the
  `bars` table by venue.
- **SC-002**: A feed whose socket is dropped without a close frame is producing
  again within its maximum silence plus its minimum connect interval, measured
  with a fake clock in CI and by hand against a live venue.
- **SC-003**: Over one hour, three symbols on one venue produce 180 archive
  objects, not 60, each holding a single symbol; and zero objects appear outside
  `raw/cex/`.
- **SC-004**: An ingest service's log at steady state stays under 10 MB a day,
  against a measured baseline of about 1.1 GB a day for the busiest.
- **SC-005**: Every service in the compose file is capped; none can fill the host
  disk with its own log.
- **SC-006**: The count of archive minutes holding each symbol, for the period in
  which they were overwritten, is a number in a note, not an impression.

## Assumptions

- **The symbol is a path component between venue and date**:
  `raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz`. It keeps the
  existing `raw/cex/<venue>/` listing prefix valid for readers, and it makes
  "everything for one symbol" a prefix, not a scan. A symbol in the filename was
  considered and rejected for the second reason. The one reader in the repository,
  `tools/record/parity_capture.py`, must then select by symbol; that is part of
  this work, not left behind.
- **The overwritten frames cannot be recovered.** `store.put` replaces an object
  and nothing versioned it. The honest remedy is to state the extent, not to
  imply a repair.
- **A threshold is configuration** (Principle X). The silence default per venue
  is a stated starting point with its basis written next to it, overridable by
  environment, not a constant buried in a method.
- **Live connections are checked by hand.** CI has no network. What CI proves is
  the wiring and the behaviour under a fake connector; what only the venue can
  prove is recorded in the implement outcome note, with the date.
- **The raw-frame logging that exists today is debugging output**, not a feature.
  Nothing downstream reads the log for it.
- **One process per symbol per venue stays.** [[REQ-WP-066]]'s reason — one
  stalled symbol must not stop the others silently — is unchanged; the key now
  reflects the topology instead of contradicting it.
