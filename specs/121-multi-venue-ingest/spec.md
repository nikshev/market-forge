---
traces: [REQ-WP-076]
status: implemented
---

# Feature Specification: The ingest daemon runs for Bybit and OKX

**Feature Branch**: `121-multi-venue-ingest`

**Created**: 2026-09-23

**Status**: Draft

**Input**: [[REQ-WP-076]] — PRD §5.2 (the Phase 2 universe) and §6.2 (one ingest
service per venue).

## Context

§5.2 names the Phase 2 universe:

> - Top 20–50 liquid Binance USDⓈ-M perpetuals;
> - Bybit linear perps;
> - OKX swaps.

§6.2's compose list names `ingest-binance` — one service per venue, by its
shape. Phase 2 therefore adds services, not parameters to the existing one.

**Most of the venue work exists; none of it is wired.** `VenuePolicy` names
`BINANCE`, `BYBIT` and `OKX`, with their keepalives **measured** on 2026-09-12
(`connectors/session.py`): Bybit closes an idle connection at ~60s with no
close frame, OKX at ~31s with code 4004, and each expects a different ping
payload. The normalisation layer exists for all three, each with its own
suite (`bybit/normalize.py`, `okx/normalize.py`).

The **live path** is Binance code, not venue-agnostic code waiting for
configuration:

- `WebsocketTransport` takes one `url_for(streams)` builder;
- `streams_for` builds `f"{symbol.lower()}@aggTrade"` — Binance's combined
  stream notation;
- `build_daemon` passes `BINANCE` and a module-level `VENUE` as constants.

### The one assumption that does not survive

Binance carries subscriptions **in the URL**: one combined-stream connection
whose frame names its stream. That is not a general shape. Bybit V5 and OKX v5
subscribe by a **message sent after connecting** — and §46 names each venue's
own documentation as the source, explicitly not an assumption that Binance's
rule generalises.

So "make the venue a value" is not a rename. It changes what connecting means
for the transport/session seam: for at least two venues the streams are not
URL parameters at all. This specification requires the venue's own rule to be
a **value carried through the live path** and pinned by tests against the
venue's documentation; which layer assembles the subscription is a planning
decision, and the seam must not assume URL-only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A daemon for a configured venue (Priority: P1)

An operator sets the venue and a symbol in configuration and gets a running
daemon: connected, subscribed, bars written with that venue in the `venue`
column, frames archived under a prefix naming the venue.

**Independent Test**: build the daemon from configuration alone with a fake
transport and a local catalog; assert the connection was made, the
subscription payload is right for the venue, bars land, and the archive prefix
names it.

**Acceptance Scenarios**:

1. **Given** configuration naming `bybit` and `BTCUSDT`, **When** the daemon is
   built, **Then** no code path reads a Binance constant for the venue.
2. **Given** the same for `okx`, **Then** the same holds.
3. **Given** a daemon that produced a finalized bar, **Then** the `bars` row's
   `venue` is the configured one, and the archive object's key starts with that
   venue's prefix.
4. **Given** an unknown venue in configuration, **Then** startup refuses,
   naming it and the known venues.

---

### User Story 2 - Each venue's stream names and subscription (Priority: P1)

Each venue's subscription follows **its own documented rule**: Binance's
combined-stream URL, Bybit's V5 subscribe message, OKX's v5 `op: subscribe`.

**Why this priority**: a wrong stream name connects and delivers nothing —
measured once with an upper-case Binance name, which is why this requirement
exists in the shape it does.

**Independent Test**: call each venue's stream/subscription builder and compare
against the exact strings its documentation gives; then run each through a fake
transport that records what was sent.

**Acceptance Scenarios**:

1. **Given** `BTCUSDT` for Binance, **Then** the stream name and URL match
   Binance's combined-stream documentation, and the case is lower.
2. **Given** `BTCUSDT` for Bybit, **Then** the subscribe message is Bybit V5's,
   with the venue's own channel/topic naming.
3. **Given** `BTCUSDT` for OKX, **Then** the subscribe message is OKX v5's, with
   the venue's own `instId` naming and `op`.
4. **Given** any two venues, **Then** neither builder is the other's with a
   string replaced — each is asserted against its own documentation.

---

### User Story 3 - Each venue's connection policy (Priority: P1)

A Bybit daemon pings with Bybit's payload and reconnects on Bybit's silence;
an OKX daemon does the same with OKX's bare-string ping and its 4004 rule.

**Independent Test**: run `StreamSession` for each venue against a fake
transport and clock; assert the sends and the reconnect decisions match the
venue's policy, not Binance's.

**Acceptance Scenarios**:

1. **Given** a quiet Bybit connection past its idle timeout, **Then** the
   session treats the silence as a drop, per its policy's "no close frame".
2. **Given** a quiet OKX connection, **Then** the policy's keepalive fires with
   the bare-string ping.
3. **Given** the same clock and traffic for the three venues, **Then** the
   decisions differ where the policies differ — proving the policy is read, not
   assumed.

---

### User Story 4 - A venue that delivers nothing is visible (Priority: P2)

A connection that succeeds and produces no frames is **reported**, not left to
look like a market with no trades.

**Why this priority**: it is the failure mode that motivated the requirement —
an upper-case stream name on Binance's combined stream connected and delivered
nothing, and it was found by measurement rather than by a message.

**Independent Test**: a fake transport accepts the connection and never
delivers; assert a counter/message names the venue, symbol and the silence,
within the venue's expected first-frame window.

**Acceptance Scenarios**:

1. **Given** a connection that delivers no frames past the expected window,
   **Then** the condition is reported with venue and symbol.
2. **Given** a venue that then delivers a frame, **Then** the report clears or
   is superseded by the frame count.
3. **Given** a normal quiet minute on a real venue, **Then** the report does not
   fire spuriously — the window is configurable, per Principle X.

---

### Edge Cases

- **One process per symbol per venue**, as [[REQ-WP-066]] established; a
  configuration naming more than one symbol is refused with the same message
  shape, now naming the venue too.
- **A venue's own symbol spelling** (`BTCUSDT` vs `BTC-USDT-SWAP` vs
  `BTC-USDT`) is not converted by this feature: the symbol is configured as the
  venue spells it, and a mismatch surfaces as the silence report above rather
  than as a guessed translation.
- **Reconnect** obeys the venue's `min_connect_interval_ns`, which is
  conservative by its own admission rather than measured.
- **The archive prefix** names the venue, so one venue's raw tier cannot be
  read as another's.
- **A partial minute** at shutdown: unchanged from [[REQ-WP-066]].

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The venue MUST be a value read from configuration and carried
  through the live path — builder, session, policy, archive prefix and the
  `venue` column. No venue constant may remain in the wiring path.
- **FR-002**: Each supported venue MUST expose its own stream/subscription
  construction, pinned by tests against that venue's documentation (Binance
  combined stream; Bybit V5; OKX v5). No venue's convention may be produced by
  substituting into another's.
- **FR-003**: Each connection MUST use its venue's `VenuePolicy` for keepalive,
  idle timeout, close-frame expectation and connect throttling.
- **FR-004**: Raw frames MUST archive under a prefix naming the venue.
- **FR-005**: Bars MUST be written with the configured venue in the `venue`
  column.
- **FR-006**: A connection that delivers no frames within a configured window
  MUST be reported, naming venue and symbol; the report MUST NOT fire for a
  normal quiet window.
- **FR-007**: An unknown venue MUST refuse at startup, naming it and the
  supported venues.
- **FR-008**: One process per symbol per venue MUST be enforced with the
  existing refusal shape.
- **FR-009**: The existing Binance deployment MUST keep working unchanged: same
  stream name, same URL, same policy as today.

### Key Entities

- **Venue**: a value naming an exchange; each carries its own stream grammar,
  subscribe mechanics and policy.
- **Subscription**: what a connection asks for — URL parameters for one venue,
  a message after connect for others.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two new services run in the stack, one for Bybit and one for OKX,
  built from configuration alone; `bars` holds rows for all three venues.
- **SC-002**: Each venue's subscription string equals its documentation's,
  asserted byte for byte.
- **SC-003**: A fake connection that delivers nothing produces a named report
  within the configured window; a connection delivering frames does not.
- **SC-004**: Zero venue constants remain in the wiring path, measured by a
  source-tree check as [[REQ-WP-073]]'s T034 and [[REQ-WP-074]]'s SC-003 do.
- **SC-005**: Binance's deployed behaviour is byte-identical before and after
  (stream names, URL, policy), proven by its existing tests passing unchanged.

## Assumptions

- The policies' measured keepalives (2026-09-12) stand; this feature consumes
  them, it does not re-measure them.
- The normalizers exist and are correct; this feature wires them, and does not
  re-specify their parsing.
- Live verification against Bybit and OKX is a deployment step: tests use fakes
  and documentation strings, and a manual connection check is recorded in the
  quickstart rather than run in CI, because a third-party venue in the fast
  gate would make every commit depend on someone else's uptime ([[REQ-INFRA-002]]).
- Symbol spellings are configured as the venue writes them; no cross-venue
  symbol mapping is introduced here (§17 owns that).
