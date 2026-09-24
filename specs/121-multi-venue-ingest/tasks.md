---
description: "Task list for REQ-WP-076 — the ingest daemon runs for Bybit and OKX"
---

# Tasks: The ingest daemon runs for Bybit and OKX

**Input**: Design documents from `/specs/121-multi-venue-ingest/`

**Tests**: REQUIRED. Every Python test carries `@pytest.mark.trace("REQ-WP-076")`;
every TypeScript source carries `// @trace: REQ-WP-076`. Write each test first and
watch it fail for the stated reason.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Backend: `src/channelflow/`, `tests/`. No frontend work for this feature.

---

## Phase 1: Setup

- [ ] T001 Record the baseline in the implement outcome note: `ingest-binance`
  is the only ingest service; `bars` table has only `binance` venue; `docker
  compose ps` shows one ingest service.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the venue abstraction and connector protocol — every user story
depends on this.

- [ ] T002 Add `VenueConnector` protocol to
  `src/channelflow/connectors/venue.py` with `# @trace: REQ-WP-076`: `connect(streams)`,
  `send(payload)`, `pong()`, `close()`, `frames` property.
- [ ] T003 [P] Write the failing tests in
  `tests/unit/connectors/test_venue_connector.py` (new): protocol methods
  exist; a fake implementation satisfies the protocol.
- [ ] T004 Add `VenueConfig` dataclass and `VENUE_REGISTRY` to
  `src/channelflow/connectors/venue.py` with `# @trace: REQ-WP-076`:
  `connector` class, `stream_builder`, `policy`, `archive_prefix`.
- [ ] T005 [P] Write the failing tests in
  `tests/unit/connectors/test_venue_registry.py` (new): registry contains
  `binance`, `bybit`, `okx`; each has the four fields; `binance` connector is
  `BinanceConnector`; `bybit` is `BybitConnector`; `okx` is `OkxConnector`.
- [ ] T006 Add `VenueConnector` import and type hint to
  `src/channelflow/pipeline/ingest.py` with `# @trace: REQ-WP-076`: change
  `StreamSession.__init__` to accept `connector: VenueConnector` instead of
  `transport: WebsocketTransport`; call `connector.connect(streams)` and read
  `connector.frames`.
- [ ] T007 [P] Write the failing test in
  `tests/unit/pipeline/test_ingest_session.py` (new): `StreamSession` accepts a
  fake `VenueConnector`, calls `connect(streams)`, reads `frames`.
- [ ] T008 Update `src/channelflow/pipeline/ingest_main.py` with
  `# @trace: REQ-WP-076`: read `CHANNELFLOW_INGEST_VENUE`, lookup
  `VENUE_REGISTRY[venue]`, build `connector = config.connector(...)`, pass to
  `IngestDaemon(venue=venue, connector=connector, ...)`; refuse if venue
  unknown or symbols empty.

**Checkpoint**: `ingest_main` can be constructed for each venue with a fake
connector; no venue constant remains in the wiring path.

---

## Phase 3: User Story 1 — A daemon for a configured venue (Priority: P1) 🎯 MVP

**Goal**: a daemon configured with venue + symbol runs end-to-end: connects,
subscribes, writes bars with the venue in the `venue` column, archives under
the venue's prefix.

**Independent Test**: build the daemon from config with a fake transport; assert
connection, subscription payload, bars written, archive prefix.

- [ ] T009 [US1] Write the failing tests in
  `tests/unit/pipeline/test_ingest_daemon.py` (new): build daemon with a fake
  `VenueConnector` that records `connect` call; assert `connect(streams)` called
  with correct streams; bars written with `venue` column = configured venue;
  `FrameArchive.prefix` ends with `/<venue>/raw/cex`.
- [ ] T010 [US1] Update `src/channelflow/pipeline/ingest.py` with
  `# @trace: REQ-WP-076`: `IngestDaemon.__init__` accepts `venue: str` and
  `connector: VenueConnector`; `FrameArchive(..., venue=venue, prefix=f"{venue}/raw/cex")`;
  `BarSink(..., venue=venue)`.
- [ ] T011 [US1] Update `src/channelflow/pipeline/ingest_main.py`: pass
  `venue` and `connector` to `IngestDaemon`; `FrameArchive` gets venue prefix.
- [ ] T012 [P] [US1] Write the failing test in
  `tests/unit/pipeline/test_archive_prefix.py` (new): `FrameArchive` with
  `venue="bybit"` produces prefix `bybit/raw/cex`; with `venue="okx"` produces
  `okx/raw/cex`.

**Checkpoint**: a daemon built from config writes bars with the right venue and
archives under the venue's prefix.

---

## Phase 4: User Story 2 — Each venue's stream names and subscription (Priority: P1)

**Goal**: each venue's stream names and subscription follow its own documented
rule; Binance's URL-parameter form does not generalise.

**Independent Test**: call each venue's stream builder and subscription message
builder; assert byte-for-byte against the venue's documentation.

- [ ] T013 [US2] Add `src/channelflow/connectors/websocket.py` with
  `# @trace: REQ-WP-076`: `binance_streams(symbols)`, `bybit_streams(symbols)`,
  `okx_streams(symbols)`; `binance_subscribe_message(streams)`,
  `bybit_subscribe_message(streams)`, `okx_subscribe_message(streams)`.
- [ ] T014 [P] [US2] Write the failing tests in
  `tests/unit/connectors/test_websocket_builders.py` (new): `binance_streams`
  produces `["btcusdt@aggTrade"]`; `bybit_streams` produces
  `["publicTrade.BTCUSDT"]`; `okx_streams` produces
  `["trades.BTC-USDT-SWAP"]`; subscription messages match the exact JSON
  strings in each venue's docs (case-sensitive, field names exact).
- [ ] T015 [US2] Add `src/channelflow/connectors/binance/connector.py` with
  `# @trace: REQ-WP-076`: `BinanceConnector` wraps `WebsocketTransport`;
  `connect(streams)` delegates to transport; `send/pong/close/frames` delegate.
- [ ] T016 [P] [US2] Write the failing tests in
  `tests/unit/connectors/test_binance_connector.py` (new): `connect` calls
  transport with correct URL; frames delegate.
- [ ] T017 [US2] Add `src/channelflow/connectors/bybit/connector.py` with
  `# @trace: REQ-WP-076`: `BybitConnector.__init__(url, subscribe_msg)`; `connect`
  opens WS, sends subscribe message, starts reader thread; frames queue.
- [ ] T018 [P] [US2] Write the failing tests in
  `tests/unit/connectors/test_bybit_connector.py` (new): `connect` sends exact
  subscribe JSON; frames queue receives frames; `send` delegates.
- [ ] T019 [US2] Add `src/channelflow/connectors/okx/connector.py` with
  `# @trace: REQ-WP-076`: `OkxConnector.__init__(url, subscribe_msg)`;
  `connect` sends OKX subscribe JSON; frames queue.
- [ ] T020 [P] [US2] Write the failing tests in
  `tests/unit/connectors/test_okx_connector.py` (new): `connect` sends exact
  OKX subscribe JSON; frames queue receives frames.

**Checkpoint**: each venue's connector builds correct streams and sends correct
subscription message; unit tests assert byte-for-byte against docs.

---

## Phase 5: User Story 3 — Each venue's connection policy (Priority: P1)

**Goal**: each venue's keepalive, idle timeout, reconnect rules are enforced by
its own `VenuePolicy`.

**Independent Test**: run `StreamSession` with each venue's policy against a
fake clock/transport; assert pings, timeouts, reconnects follow that venue's
rules, not Binance's.

- [ ] T021 [US3] Write the failing tests in
  `tests/unit/pipeline/test_stream_session_policies.py` (new): `StreamSession`
  with `BYBIT_POLICY` pings with Bybit payload, reconnects on silence (no close
  frame); with `OKX_POLICY` pings bare `ping`, reconnects on code 4004; with
  `BINANCE_POLICY` uses websocket ping/pong and 24h idle timeout.
- [ ] T022 [US3] Update `src/channelflow/pipeline/ingest.py`: `StreamSession`
  uses `connector.pong()` on ping frame; reconnect logic reads
  `policy.idle_timeout_ns`, `policy.ping_payload`, `policy.expects_close_frame`.

**Checkpoint**: each venue's connection behaviour follows its own policy.

---

## Phase 6: User Story 4 — A venue that delivers nothing is visible (Priority: P2)

**Goal**: a connection that succeeds but delivers no frames is reported within a
configurable window; normal quiet windows do not trigger it.

**Independent Test**: fake transport accepts connection, never delivers frames;
assert warning logged with venue, symbol, silence duration; a normal quiet
minute does not trigger.

- [ ] T023 [US4] Write the failing test in
  `tests/unit/pipeline/test_silence_detector.py` (new): `IngestDaemon` with
  fake connector that delivers no frames; after `silence_window_ns` passes,
  warning logged with `venue`, `symbol`, `silence_ns`; a normal frame resets
  the timer and no warning fires.
- [ ] T024a [P] [US4] Add silence detector to `src/channelflow/pipeline/ingest.py`
  with `# @trace: REQ-WP-076`: `_last_frame_ns: dict[tuple[str,str], int]`;
  `_check_silence(now_ns)` called periodically; logs warning with
  `venue`, `symbol`, `silence_ns`; configurable multiplier
  `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER` (default 2.0).

**Checkpoint**: a silent connection is reported; a quiet minute is not.

---

## Phase 7: Polish & Cross-Cutting

- [ ] T025 Add `CHANNELFLOW_INGEST_VENUE`, `CHANNELFLOW_INGEST_SYMBOLS_BYBIT`,
  `CHANNELFLOW_INGEST_SYMBOLS_OKX`, `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER`
  to `src/channelflow/settings.py` with `# @trace: REQ-WP-076`.
- [ ] T026 Update `docker-compose.yml`: add `ingest-bybit` and `ingest-okx`
  services (same build as `ingest-binance`, env vars for venue and symbols).
- [ ] T027 Update `docker-compose.yml` for `api` service: add
  `CHANNELFLOW_INGEST_VENUE` (not strictly needed but consistent).
- [ ] T028 Update `.env.example`: add `CHANNELFLOW_INGEST_VENUE=`,
  `CHANNELFLOW_INGEST_SYMBOLS_BYBIT=`, `CHANNELFLOW_INGEST_SYMBOLS_OKX=`,
  `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER=2.0` with comments.
- [ ] T029 [P] Write the failing test in
  `tests/unit/test_settings.py` for the new env vars.
- [ ] T030 [P] Update `docs/deployment.md`: document the two new services,
  the new env vars, and that `CHANNELFLOW_INGEST_VENUE` is required per
  process.
- [ ] T031 Run the quickstart against the running stack: `docker compose
  up -d --build ingest-bybit ingest-okx`; verify bars for `bybit` and `okx`
  appear in the API; verify archive prefixes in MinIO.
- [ ] T032b Run the gates: `make lint`, `make typecheck`, `make test-fast`;
  `cd apps/web && npx tsc --noEmit && npx vitest run && npx vite build`;
  then `make graph && make validate`.

---

## Dependencies & Execution Order

- **Phase 2** blocks every story: no story has a connector without the
  protocol/registry.
- **US1 (Phase 3)** before **US2 (Phase 4)**: US1 builds the daemon that US2's
  connectors plug into.
- **US2 (Phase 4)** and **US3 (Phase 5)** can run in parallel after Phase 2;
  US4 (Phase 6) depends on US1's daemon existing.
- **Phase 7** last.

### Parallel Opportunities

Every `[P]` test task is a new file or independent assertion; they can be
written together. Non-`[P]` tasks each extend one module and must be sequential
within their phase.

---

## Notes

- **Write the test first and watch it fail.** T003, T005, T007, T009, T015, T017, T019, T021, T022, T023 are the
  gates: if they pass before the implementation, the test is not guarding the
  right thing.
- **FR/SC traceability**: each user story maps to FRs/SCs:
  US1→FR-001,004,005,008,009 / SC-001,004,005
  US2→FR-002 / SC-002
  US3→FR-003 / SC-004
  US4→FR-006,007 / SC-003
  FR-009/SC-005 (Binance frozen) is the regression guard across all stories.
- **Test/implementation ordering**: where a phase lists an
  implementation task before its test task (T002/T003, T004/T005, T006/T007,
  T008/T009, T010/T011, T012/T013, T014/T015, T020/T021, T023/T024), the **test task runs first** — the pair
  is one change, and the list keeps each module next to its tests for
  readability. T009 in particular: if it passes before T010, the mock is not
  capturing the requests.
- The Python tasks run in the fast gate. No TypeScript work for this feature.
- `make test-fast` is the regression check; `make validate` is the full gate.