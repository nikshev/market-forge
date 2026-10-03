---
description: "Task list for REQ-WP-078 — the multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded"
---

# Tasks: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded

**Input**: Design documents from `/specs/123-ingest-resilience/`

**Tests**: REQUIRED. Every test carries `@pytest.mark.trace("REQ-WP-078")`. Write each
test first and watch it fail **for the stated reason** — a test that fails for a
different reason has not shown you what it guards, and one that passes on first run
has shown you nothing.

**The thread through every test below** (spec, "Seven defects, one cause"): each is
driven through the **join** — `build_daemon`, a fake connector whose reader dies
without a close frame, the compose file read as data. A test of the part was green
beside all seven defects. Where a task could be satisfied by a test that would also
pass against the broken wiring, it says what to assert instead.

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project: `src/channelflow/`, `tests/`, `tools/` at repository root.

---

## Phase 1: Setup

- [x] T001 Re-measure and record the **before** in the implement outcome note, because every figure moves while the defects are live: log bytes per minute for each ingest service (baseline at plan time 57,152 to 576,722), archive object counts under `raw/cex/binance/`, `binance/raw/cex/binance/` and `bybit/raw/cex/bybit/` (24,825 and 487 MB at plan time, +2 a minute), and the rows of `bars` per venue (no `okx` at plan time) *Done in part (2026-10-03): log bytes per minute were re-measured before the deploy; the archive object counts and the `bars` rows per venue were not re-counted, so the outcome note has no "before" for them beyond the plan-time figures above.*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: a venue's policy has one home and carries the fields every later story
reads. Nothing below can state a silence limit or a lifetime until there is one policy
to state it on.

- [x] T002 Write the failing test in `tests/unit/connectors/test_policies_single_home.py` that imports every module of `channelflow.connectors`, collects every `VenuePolicy` instance found as a module attribute, groups them by `.venue`, and asserts each venue has exactly one **distinct** policy. Fails today because `BINANCE`/`BINANCE_POLICY`, `BYBIT`/`BYBIT_POLICY` and `OKX`/`OKX_POLICY` differ, and the failure message must name the venue and the two modules
- [x] T003 [P] Write the failing test in `tests/unit/connectors/test_policies_single_home.py` that the guard **can** fail: build two differing policies for one venue in the test and assert the collector reports them. A guard that has never seen the thing it forbids guards nothing
- [x] T004 [P] Write the failing test in `tests/unit/connectors/test_venue_policies_values.py` pinning the kept values and why: Binance `stream_lifetime_ns == 24 h` and `idle_timeout_ns is None`; Bybit idle 60 s, ping 20 s; OKX idle 30 s, **ping 15 s**. Fails today on Binance (the live policy has the reverse) and on OKX's ping interval (20 s in `venue.py`). The OKX line carries the comment that 15 s is what `session.py` records as measured to survive a hundred seconds
- [x] T005 Add `max_silence_ns: int | None = None` and `max_connect_backoff_ns: int = 60 * SECOND_NS` to `VenuePolicy` in `src/channelflow/connectors/session.py`, and set `max_silence_ns = 60 * SECOND_NS` on `BINANCE`, `BYBIT` and `OKX`, **with the basis written in the comment beside each value** (FR-005 asks for a stated basis, and a number without one is the constant Principle X forbids): the longest real gaps measured on 2026-10-02 were 22.2 s (Bybit BTCUSDT, 360 minutes) and 11.2 s (SOLUSDT, 309 minutes), and the 64.1 s gap that also appeared was this project's own container restart. Binance gets back nothing but what `session.py` already has: `stream_lifetime_ns`, no idle timeout
- [x] T006 [P] Write the failing tests in `tests/unit/connectors/test_venue_policy_validation.py` for the three additions to `__post_init__`: `max_silence_ns` is positive when set; `max_silence_ns` is greater than `client_ping_interval_ns` when both are set (a limit under the keepalive would reconnect a healthy quiet connection between two pongs); `max_connect_backoff_ns >= min_connect_interval_ns`. Each fails today because the field does not exist
- [x] T007 Add the `__post_init__` checks of T006 to `VenuePolicy`
- [x] T008 Add `silence_limit_ns(policy) -> int | None` to `session.py`: `max_silence_ns` if set, else `idle_timeout_ns` when the venue does not announce close, else `None`
- [x] T009 [P] Write the failing test in `tests/unit/connectors/test_silence_limit.py` for T008's three branches, using `HYPERCORE` for the fallback — **it has no `max_silence_ns` and does not announce close, so it must still reconnect at its idle timeout**, which is the behaviour the fallback exists to keep
- [x] T010 Make `src/channelflow/connectors/venue.py` import `BINANCE`, `BYBIT`, `OKX` from `session.py`; delete `BINANCE_POLICY`, `BYBIT_POLICY`, `OKX_POLICY`; update `src/channelflow/connectors/__init__.py`, which re-exports them
- [x] T011 (**lands in the same commit as T010** — between them the suite is red) Update the tests that import or pin the deleted constants: `tests/unit/connectors/test_venue_connector.py` (`TestVenuePolicies`, **replacing `test_binance_policy`'s assertion of a 24-hour idle timeout with one of a 24-hour lifetime** — that test pinned the defect as correct) and `tests/unit/pipeline/test_stream_session_policies.py`

**Checkpoint**: one policy per venue, the two fields exist, and T002 is green.

---

## Phase 3: User Story 2 — A dead feed comes back (Priority: P1) 🎯 MVP

**Goal**: for every venue, a connection that ends is reopened, whatever ended it.

**Independent Test**: a fake connector whose reader dies **without** a close frame, on a
policy with `announces_close=True`.

### Tests first

- [x] T012 Update `tests/unit/connectors/test_venue_connector.py::TestVenueConnectorProtocol::test_protocol_has_required_methods` to expect `alive`. Fails today because the protocol has no such property
- [x] T013 Give **every** test fake of `VenueConnector` an `alive` property that is true until told otherwise: those in `tests/unit/pipeline/test_ingest.py`, `test_ingest_daemon.py`, `test_ingest_session.py`, `test_silence_detector.py`, `test_stream_session_policies.py` and `tests/unit/parity/test_live_replay_parity.py`. Put the controllable one in one shared helper (`tests/unit/pipeline/fakes.py`) with `kill()` and `revive()`, and have the others subclass it where they can. `StreamSession` will read `alive` strictly — **not** `getattr(..., True)`, which would turn a missing method into a connection that is always fine
- [x] T014 [P] Write the failing test in `tests/unit/pipeline/test_session_reconnect.py`: a session whose connector has been `kill()`ed, under a policy with `announces_close=True`, is reconnected by the next `tick`. Fails today because `tick` only reconnects on silence and only when the venue does not announce close
- [x] T015 [P] Write the failing test in the same file: a feed silent past `silence_limit_ns` is reconnected **for an announce-close venue**, and is **not** reconnected one nanosecond before the limit
- [x] T016 [P] Write the failing test in the same file: over **1,000 ticks** of a persisting silence the log holds exactly one WARNING (entry) and, after the feed returns, exactly one INFO (recovery) — count the records with `caplog`, do not assert on text. Fails today because the daemon warns on every step
- [x] T017 [P] Write the failing test in the same file: on a policy with `stream_lifetime_ns = 24 h`, a fake clock advanced past 24 hours makes `tick` reconnect. Uses the corrected Binance policy, so it fails against the live one
- [x] T018 [P] Write the failing test in the same file for the schedule: a connector whose `connect()` raises, ticked repeatedly, is attempted at `min_connect_interval × 2ⁿ` capped at `max_connect_backoff_ns`; attempts are never closer than `min_connect_interval_ns`; **`tick` does not raise**. Fails today because `_reconnect` lets `NotConnected` out of `tick`
- [x] T019 [P] Write the failing test in the same file for the log under refusal: 200 failed attempts produce a number of WARNING records that is O(log 200) — assert `<= 12` — and one INFO on recovery that states the attempts it took
- [x] T020 [P] Write the failing test in the same file for the **false recovery**: `connect()` returns, the reader dies again on the next tick; the failure count and the backoff carry over rather than resetting. Bybit and OKX `connect()` only starts a thread, so this is their normal failure shape
- [x] T020a [P] Write the failing test in `tests/unit/pipeline/test_session_reconnect.py`, **through `IngestDaemon`** and not the session alone: add frames in the middle of a minute, `kill()` the connector, let `tick` reconnect, add more frames in the same minute, flush — and assert the archive object for that minute holds the frames from **before and after** the reconnect, and that a bar spanning it is built from both. The spec's edge case ("the bars builder and the archive buffer outlive the socket") and `contracts/connector.md` guarantee 5 are otherwise untested, and a plausible implementation — rebuilding the daemon's collaborators on reconnect — would pass every other test here and lose a minute of frames each time
- [x] T021 [P] Write the failing tests in `tests/unit/connectors/test_reader_endings.py` for each real connector's reader, with `websockets.sync.client.connect` replaced: it raises on open; `recv` raises mid-stream; the venue closes with a code. Each asserts `alive` becomes false **and** a WARNING naming the venue and the exception text or close code was logged. Fails today for OKX (no log at all) and for `WebsocketTransport` (the failure is stored in `_failure`, read only by `connect()`)

### Implementation

- [x] T022 Add `alive` to the `VenueConnector` protocol in `src/channelflow/connectors/venue.py`
- [x] T023 Implement `alive` and the logging of why a reader ended in `src/channelflow/connectors/websocket.py` (`WebsocketTransport`: thread alive and no `_failure`; log the failure where it is stored), `binance/connector.py` (delegate), `bybit/connector.py` and `okx/connector.py` (thread alive; every exit path logs once at WARNING with the venue)
- [x] T024 Rewrite `StreamSession.tick` and `_reconnect` in `src/channelflow/connectors/session.py` per `contracts/connector.md`: the three grounds in order, `next_attempt_ns`, `consecutive_failures`, `down_since_ns`, `down_reason`, a module logger, `_reconnect` catching a failing `connect()`, logs at attempts 1, 2, 4, 8… and one INFO on recovery. `start()` still raises
- [x] T025 Remove `IngestDaemon._check_silence`, `silence_window_multiplier` and `_last_frame_ns` from `src/channelflow/pipeline/ingest.py`: the session now owns silence. Rewrite `tests/unit/pipeline/test_silence_detector.py` against the session, **keeping every behaviour it asserted that still holds** (a normal frame resets the timer; a silent connection is reported) and deleting only what asserted the daemon's own warning
- [x] T026 Replace the multiplier configuration: remove `SILENCE_WINDOW_MULTIPLIER` / `DEFAULT_SILENCE_WINDOW_MULTIPLIER` and `IngestSettings.silence_window_multiplier` from `src/channelflow/pipeline/ingest_main.py`; add `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` → `IngestSettings.max_silence_ns` (`None` when unset), applied in `build_daemon` with `dataclasses.replace(policy, max_silence_ns=…)`. Rewrite `tests/unit/test_settings_ingest.py`: unset gives `None`; a value is converted to nanoseconds; zero, negative and non-numeric are refused naming the variable

**Checkpoint**: T012–T021 green; a killed reader, a silent feed and an elapsed lifetime
each reconnect, on every venue, with a bounded log.

---

## Phase 4: User Story 1 — Every configured venue delivers (Priority: P1)

**Goal**: OKX connects and subscribes the way OKX expects, and a refusal is readable.

**Independent Test**: the connector **the daemon builds**, read back.

### Tests first

- [x] T027 Write the failing test in `tests/unit/pipeline/test_build_daemon_seams.py`: `build_daemon(venue="okx", symbol="BTC-USDT-SWAP", …)` yields a connector whose `_url` is `wss://ws.okx.com:8443/ws/v5/public` and whose `_subscribe_msg`, parsed as JSON, is `{"op":"subscribe","args":[{"channel":"trades","instId":"BTC-USDT-SWAP"}]}` — **`instId` equal to the instrument, with no `trades.` prefix**. Fails today on both: the URL answers 404 and the prefix is in `instId`
- [x] T028 [P] Write the failing test in the same file for Bybit through `build_daemon`: `_url` is `wss://stream.bybit.com/v5/public/linear` and the subscribe argument is `publicTrade.BTCUSDT`. Passes today by construction; it exists so moving the URL into the registry (T031) cannot change it silently
- [x] T029 [P] Write the failing test in `tests/unit/connectors/test_rejection_frames.py` for `rejection(venue, frame)` against **the frames captured live on 2026-10-02**, verbatim from `contracts/connector.md`: OKX's error frame returns its `msg`; Bybit's `success:false` frame returns its `ret_msg`; Binance returns `None` for anything; a non-JSON string, a JSON array and an ordinary trade frame return `None` and **never raise**. Fails today because the function does not exist
- [x] T030 [P] Write the failing test in `tests/unit/connectors/test_reader_endings.py` that an OKX and a Bybit reader fed a rejection frame **queue it** (the archive keeps what the venue said) **and** log one WARNING quoting the venue's message. Fails today: nothing reads the frame

### Implementation

- [x] T031 Add `url: str | None` and `subscribe_message: Callable[[Sequence[str]], str | None]` to `VenueConfig` in `venue.py` and fill the registry; `okx_subscribe_message` and `bybit_subscribe_message` take **symbols**, not stream labels. Remove `VenueConfig.archive_prefix`. Update `tests/unit/connectors/test_venue_connector.py` where it reads either
- [x] T032 Rewrite `build_daemon` in `ingest_main.py` to take `url` and `subscribe_message(symbols)` from the registry; Binance keeps its one branch because it subscribes by URL. **Delete `_connector_for_venue`** — it builds streams from the literal `"placeholder"` and its result is read by nothing
- [x] T033 Add `rejection(venue, frame)` to `venue.py` and call it for every frame in the Bybit and OKX readers, logging at WARNING as `"<venue> rejected the request: <message>"` and queueing the frame regardless
- [x] T034 **Live check, by hand, recorded in the implement outcome note with the date**: after rebuilding, `docker compose logs --since 2m ingest-okx` shows a connected line, no `silent connection` and no `rejected`; after fifteen minutes `GET /api/v1/bars?venue=okx&symbol=BTC-USDT-SWAP&timeframe_ns=60000000000` returns bars. CI has no network, so this is the only proof that OKX delivers *Done 2026-10-03 through the API itself: 810 OKX bars at 05:18 UTC, the first opening 2026-10-02 15:38 UTC, and the newest six minutes old.*

**Checkpoint**: T027–T030 green; OKX has delivered a bar.

---

## Phase 5: User Story 3 — The raw archive is where a reader looks, and keeps every symbol (Priority: P1)

**Goal**: one object per venue, symbol and minute, under `raw/cex/`; and the objects
already written are moved there.

**Independent Test**: two symbols of one venue, flushed in one minute, read back.

### Tests first

- [x] T035 Write the failing test in `tests/unit/pipeline/test_build_daemon_seams.py`: `build_daemon` with `settings.archive_uri` **read from the compose file** — the `CHANNELFLOW_ARCHIVE_URI` an ingest service is actually given (`s3://${MINIO_BUCKET}/raw/cex`), with `MINIO_BUCKET` taken from `.env.example` — and a recording store; a literal copied into the test would let the compose value drift away from what is tested (FR-011 says "the deployment's own"), archive one frame for each of Binance, Bybit and OKX, and assert for the written key: the venue occurs **exactly once**; it starts with `raw/cex/`; it contains the symbol **in the configured spelling**. Fails today with `binance/raw/cex/binance/…` — the key as a string is the thing to assert on here, because this is the test whose job is the prefix the wiring builds
- [x] T036 [P] Write the failing test in `tests/unit/pipeline/test_archive_symbol.py`: two `FrameArchive`s of one venue with different symbols, one shared store, frames added in the same minute and both flushed, give **two** objects; read each back with `read_frames` and assert it holds **only its own symbol's frames**. Assert on the frames and not on the keys: the earlier mistake was a key that looked right. Fails today because `FrameArchive` has no `symbol` and both write one key
- [x] T037 [P] Write the failing test in the same file: a `FrameArchive` with an empty symbol, a symbol containing `/`, or an empty venue raises `ValueError`. A slash would nest and the key would stop meaning what its parts say
- [x] T037a [P] Write the failing test in `tests/unit/pipeline/test_build_daemon_seams.py`: `build_daemon` for Binance or Bybit with a symbol that is not upper-case (`btcusdt`) raises `MissingConfiguration` naming the variable; OKX's `BTC-USDT-SWAP` is accepted as written. The live key uses the symbol as configured and the migration (T045) writes the upper-case spelling; if a deployment configured `btcusdt` the two would split one instrument across `btcusdt/` and `BTCUSDT/`. Fails today because nothing checks
- [x] T038 [P] Write the failing test in the same file: `flush()` with nothing buffered logs nothing at INFO or above, and `flush()` that writes logs exactly once. Fails today: it logs at INFO on every call, which is Bybit's five-a-second line

### Implementation

- [x] T039 Add `symbol` to `FrameArchive` in `src/channelflow/pipeline/archive.py`, validate it, make `key_for` return `{prefix}/{venue}/{symbol}/{YYYY}/{MM}/{DD}/{HHMM}.jsonl.gz`, and make `flush` log only when it writes (DEBUG otherwise); `S3ObjectStore.put`'s success line goes to DEBUG
- [x] T040 Make `build_daemon` pass the path component of `CHANNELFLOW_ARCHIVE_URI` unchanged, the registry's venue, and the configured symbol — **no venue in the prefix**
- [x] T040a Make `build_daemon` refuse a Binance or Bybit symbol that is not upper-case, naming the variable (T037a; FR-018)
- [x] T041 Update the existing tests that assert the old key shape: `tests/unit/pipeline/test_archive_prefix.py`, `tests/unit/pipeline/test_ingest.py` (lines ~330 and ~671), `tests/unit/pipeline/test_ingest_daemon.py` (~137) and `tests/unit/parity/test_live_replay_parity.py`. Each now builds the archive **through the daemon wiring** where it can, because that is what the old ones did not
- [x] T042 Factor `archive_prefix(venue, symbol) -> str` out of `tools/record/parity_capture.py`, add the required `--symbol`, and list `raw/cex/<venue>/<symbol>/`. Write the failing test for `archive_prefix` first: it returns `raw/cex/binance/BTCUSDT/`, and the listing prefix of two symbols never overlaps (`ETHUSDT/` is not a prefix of anything under `BTCUSDT/`, and neither is a prefix of the other)

### The migration

- [x] T043 Write `tests/unit/pipeline/fake_s3.py`: an in-memory client with exactly `list_objects_v2` (with `ContinuationToken`), `get_object`, `head_object`, `copy_object`, `delete_object` and `put_object`, ETags derived from content, and hooks to **corrupt a copy** and to **raise between copy and delete**. `moto` is not a dependency of this project. Write the failing tests of the fake itself first: a copy has the source's ETag; a corrupted copy does not
- [x] T044 [P] Write the failing tests in `tests/unit/pipeline/test_archive_rekey.py` for **key parsing**: layout A (`raw/cex/<venue>/<Y>/<M>/<D>/<HHMM>.jsonl.gz`) and layout B (`<venue>/raw/cex/<venue>/…`) parse to venue and minute; a key matching neither is refused with the reason `key matches no known layout`
- [x] T045 [P] Write the failing tests in the same file for **attribution**: Binance frames `{"stream":"btcusdt@aggTrade",…}` attribute to `BTCUSDT` (upper-cased to the configured spelling, never the lower-case label); Bybit `{"topic":"publicTrade.BTCUSDT",…}` to `BTCUSDT`; OKX `{"arg":{"instId":"BTC-USDT-SWAP"},…}` to `BTC-USDT-SWAP`; a pong, a subscribe acknowledgement and an OKX `event` frame are ignored for attribution; an object of only those is refused `no attributable frame`; an object naming two symbols is refused `several symbols: […]` **and is left where it is**
- [x] T046 [P] Write the failing tests in the same file for **safety**, using the fake: a destination that already holds identical bytes → `AlreadyThere`, source removed; a destination holding **different** bytes → refused, nothing deleted; a corrupted copy → **the source is not deleted**; an exception between copy and delete → the source remains, and a second run finishes the removal; **dry-run changes nothing** (assert the store's contents are equal before and after); a second `--apply` reports nothing to move
- [x] T047 [P] Write the failing tests in the same file for the **report**: `minutes_present` and `minutes_expected` per `(venue, symbol)` over a fixture in which three symbols alternate minutes, so each ends up missing two minutes in three; the report states the shortfall as a number
- [x] T048 Implement `src/channelflow/pipeline/archive_rekey.py`: the pure parts (key parsing, attribution, `MigrationDecision`, the report) and a thin S3 adapter, with `python -m channelflow.pipeline.archive_rekey [--venue V]… [--apply]`, dry-run by default, credentials from the same environment `settings_from_env` reads. It lives in `src/` because the application image copies `src/` only

**Checkpoint**: T035–T048 green. T049 and T050, which move the objects already written,
are in Phase 7 because they must run **after** the deploy (T062): only a rebuilt container
stops writing to the old keys, and the tool is in the image only after the rebuild.

---

## Phase 6: User Story 5 — The log is bounded (Priority: P2)

**Goal**: an ingest service logs events, not traffic, and every service is capped.

**Independent Test**: a recorded segment run at INFO; the compose file read as YAML.

### Tests first

- [x] T051 Write the failing test in `tests/unit/pipeline/test_ingest_logging.py`: run a daemon over the recorded Binance fixture (`RECORDED`) for many steps with `caplog.set_level(INFO)` and assert **no** record from `channelflow.pipeline`, `channelflow.bars` or `channelflow.connectors` at INFO or above except connect and close events. Fails today: `BarBuilder.add called…`, `_finalize_ready`, `Normalized N trade(s)` and the flush line are all INFO
- [x] T052 [P] Write the failing test in the same file that importing `channelflow.pipeline.ingest_main` does not add a handler to the root logger or change its level, and that `configure_logging()` honours `CHANNELFLOW_LOG_LEVEL` (default INFO; an unknown value is refused naming the variable). Fails today: `basicConfig` runs at import
- [x] T053 [P] Write the failing test in `tests/unit/deploy/test_compose_logging.py`: read `docker-compose.yml` with PyYAML; **every** service, including `minio_init` and any added later, has `logging.options.max-size`, and none is empty. Fails today: there is no `logging:` anywhere. Also assert the test **can** fail: a service dict without `logging` makes the checking function report that service

### Implementation

- [x] T053a [P] Write the failing test in `tests/unit/deploy/test_compose_logging.py`: **every `ingest-*` service lists `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` and `CHANNELFLOW_LOG_LEVEL` in its `environment`**. Compose forwards only the variables a service names, so a setting added to `.env.example` and the settings reader is unreachable in the deployment — FR-005's "configurable" would hold in the code and not on the host. Fails today: neither appears
- [x] T054 Move the per-trade, per-frame and per-step lines to DEBUG at their source: `src/channelflow/bars/builder.py` (four calls), `src/channelflow/pipeline/ingest.py` (`Normalized`), `src/channelflow/connectors/bybit/connector.py` (`Received raw frame`, `Received frame`, `Waiting`). Connect, close and error lines stay
- [x] T055 Replace the import-time `logging.basicConfig` in `ingest_main.py` with `configure_logging()` called from `main()`, reading `CHANNELFLOW_LOG_LEVEL`
- [x] T056 Add the shared `x-logging` block to `docker-compose.yml` and `logging: *default-logging` to every service; `max-size: ${CHANNELFLOW_LOG_MAX_SIZE:-20m}`, `max-file: "${CHANNELFLOW_LOG_MAX_FILE:-3}"`
- [x] T056a Pass `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` and `CHANNELFLOW_LOG_LEVEL` through every ingest service's `environment` as `${…:-}` (empty means unset, as `settings` already treats a blank value), and confirm the settings reader treats a blank `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` as unset rather than failing to parse `""`
- [x] T057 Add `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS`, `CHANNELFLOW_LOG_LEVEL`, `CHANNELFLOW_LOG_MAX_SIZE` and `CHANNELFLOW_LOG_MAX_FILE` to `.env.example` with comments, and **remove** `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER` wherever it appears there and in `docs/deployment.md`. `tests/unit/docs/test_deployment_doc.py` fails if a variable is in one and not the other

**Checkpoint**: T051–T053 green; the compose file caps every service.

---

## Phase 7: Mutation, deployment and Polish

- [x] T058 **First**, and again after every task that edits a mutated source (T024, T025, T032, T039, T040, T054): run `tests/tools/test_mutate.py` — `ingest.toml` went red on 2026-10-02 because REQ-WP-076 rewrote the code four of its patterns pointed at, and the gate was not installed to say so; a pattern that no longer matches is an error, not a skip, and an edit that removes one must repair the spec in the same commit. **Then** extend `tests/mutations/session.toml`, `archive.toml` and `ingest.toml` with mutations for the new behaviour, each aimed at one decision of this change: the `alive` check removed from `tick`; silence reconnect restricted again to `not announces_close`; `max_silence_ns` ignored; the backoff cap removed; a failed `connect()` allowed out of `_reconnect`; the symbol dropped from `key_for`; the venue prefixed twice again in `build_daemon`. Run `python -m tools.mutate`. **A survivor needs either a test that kills it or a written reason**; the tool refuses one without
- [x] T059 Update `docs/deployment.md`: the archive layout and where a reader looks; that a connection that ends is reopened and what the log says when it is; the four new variables; the log cap and that it applies on recreate; the re-key tool and that it defaults to a dry-run. The doc's service count and names must stay true (`test_every_running_service_is_described`)
- [x] T060 Add a dated note to `## Notes` of [[REQ-WP-076]] — human territory — that it reached `implemented` with a green suite while one venue in three delivered, that [[REQ-WP-078]] is the repair, and what the repair found. The same treatment `REQ-PHASE-1` got, and for the same reason
- [x] T061 `make lint`, `make typecheck` (mypy strict over `src/`: the new `alive` property and the registry's `Callable` fields are the likely edges)
- [x] T062 Rebuild and recreate: `docker compose up -d --build`. The log cap applies to a container when it is recreated, not when the file changes. **Expect every service to be recreated**, because the logging block changes every service's configuration: up to fifteen bars buffered per ingest process are lost (the documented `FLUSH_EVERY_BARS` trade), the API is briefly unavailable, and `postgres` and `minio` restart on their bind-mounted data. Compose addresses them by name now (`1cf4edb`), so the IP swap that a recreate caused on 2026-10-02 cannot recur
- [x] T049 **Dry-run against the live bucket, and record the whole report in the implement outcome note**: counts per `(venue, symbol)`, minutes present against expected — **this is the answer to FR-014** — and every refusal with its reason. Run it in the rebuilt `api` container (`docker compose exec -T api python -m channelflow.pipeline.archive_rekey`). Do not proceed to T050 until the refusals are read: a non-zero count of multi-symbol objects means something other than the overwrite produced them
- [x] T050 Run with `--apply`, then run again; record both reports. The second must have nothing to move. Verify afterwards by S3 listing that the object counts at the three old prefixes are what the report said remained, and that the sum moved equals the sum before. **This and T049 are the only tasks that cannot be undone by `git revert`**
- [x] T063 **Live proofs, recorded in the implement outcome note**, from `quickstart.md`: the network-disconnect reconnect (§2, finished with `--force-recreate`); the archive count one hour after deploy, expecting about 180 objects for three symbols and none at the bucket root (§3); log bytes per minute for each ingest service **after** (§5), beside the T001 before, against SC-004's ceiling stated as a number: **10 MB a day is 6,944 bytes a minute**, and any ingest service above it fails the task *Done, with one deviation: the network-disconnect proof was not finished with `--force-recreate`; the daemon recovered by itself with `restarts=0`, so there was nothing to recreate.*
- [x] T064 Write the implement outcome note: the before and after of T001 and T063, both migration reports, OKX's first bar, and what each mutation survivor was and why it was accepted
- [x] T065 `make graph && make validate`

---

## Dependencies & Execution Order

- **Phase 2** blocks every story: there is nothing to put `max_silence_ns` on until a venue has one policy.
- **Phase 3 (US2)** before **Phase 4 (US1)**: US1's registry change (T031) rebuilds `VenueConfig` and its tests assume policies already come from `session.py`. US2 also changes the `VenueConnector` protocol and every fake once, so doing it before US1 means the fakes are touched once.
- **Phase 5 (US3)** is independent of 3 and 4 and may run beside them.
- **T049 and T050 follow T062, not T040.** What stops new objects being written to the old keys is a rebuilt container, not merged code, and the tool is in the image only after the rebuild. Moving objects first would race with the old daemons still writing them.
- **T049 before T050**: the dry-run is read before anything is applied.
- **Phase 6 (US5)** after Phase 3: T054 demotes lines in `connectors/`, and the session's own logging (T024) is what T051 must find quiet.
- **T062** needs every code task above it; **T049, T050** need T062; **T063** needs T062 and an hour.

### Parallel Opportunities

Every `[P]` task is a test in its own file or an independent assertion in a file written
in the same phase. Within a phase the implementation tasks each edit one module and are
sequential.

---

## Notes

- **Write the test first and watch it fail for the stated reason.** T035 in particular:
  if it passes before T040, the fixture is wrong, not the code — it must reproduce
  `binance/raw/cex/binance/…`.
- **T034 and T063 are not CI.** CI has no network. They are the only proof that OKX
  delivers and that a real socket is reopened, and a feature closed without them is
  closed on fakes alone — the exact condition under which REQ-WP-076 was closed.
- **The tasks that touch the live bucket (T049, T050) are the only ones that cannot be
  undone by `git revert`.** The tool's design — copy, verify, delete last — is what makes
  them safe; the order above is what makes them deliberate.
- **Until T062 and T050 land, ETH and SOL keep overwriting each other's archive minutes.**
  Nothing in this list is faster than that, and no stopgap is proposed: one would create a
  fourth key layout to migrate.

---

## Coverage

Every functional requirement and success criterion of `spec.md`, and the tasks that
satisfy it. Written out because the tasks above name `FR-014` and nothing else by
identifier, so the mapping would otherwise live only in a reader's head.

| Requirement | Tasks |
|---|---|
| FR-001 OKX endpoint and instrument | T027, T031, T032, T034 |
| FR-002 test reads the connector the wiring built | T027 |
| FR-003 refusals and reader endings logged | T021, T023, T029, T030, T033 |
| FR-004 reconnect when the reader has ended | T012–T014, T022–T024 |
| FR-005 silence limit, own field, configurable, basis stated | T004–T009, T026, T056a |
| FR-006 silence reconnects; logged on entry and recovery | T015, T016, T024 |
| FR-007 Binance lifetime | T004, T005, T017 |
| FR-008 interval respected; log bounded under refusal | T018–T020, T024 |
| FR-009 one definition per venue, guarded | T002, T003, T010, T011 |
| FR-010 key: venue once, under `raw/cex/`, symbol | T035, T039, T040 |
| FR-011 test through the wiring, deployment's own URI | T035 |
| FR-012 two symbols, two objects, frames read back | T036 |
| FR-013 migration by attributed symbol, verified, refusing | T043–T050 |
| FR-014 extent overwritten, per symbol | T047, T049, T064 |
| FR-015 nothing at INFO per step; no repeated line | T016, T038, T051, T054 |
| FR-016 every service capped; test reads the file | T053, T056 |
| FR-017 log bytes before and after recorded | T001, T063, T064 |
| FR-018 Binance and Bybit symbols must be upper-case | T037a, T040a |
| SC-001 every venue delivers within a flush interval | T034, T063 |
| SC-002 dropped socket recovers within limit plus interval | T015, T017, T063 |
| SC-003 180 objects an hour for three symbols | T036, T063 |
| SC-004 log under 10 MB a day (6,944 B/min) | T051, T063 |
| SC-005 every service capped | T053, T056 |
| SC-006 overwritten minutes as a number | T047, T049 |
| Edge: a reconnect mid-minute keeps what is held | T020a |
