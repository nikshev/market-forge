# Implementation Plan: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded

**Branch**: `123-ingest-resilience` | **Date**: 2026-10-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/123-ingest-resilience/spec.md`

## Summary

Seven defects, one cause: the tests exercised the pieces and the faults were in the
joins. The plan therefore does two things at once. It changes the code at each join
— the connector asks "is my reader alive", the session reconnects on that and on
silence for every venue, the archive key carries the symbol, a venue's endpoint and
subscription live in the one registry the daemon reads — and it puts a test **at
each join**, driven through `build_daemon` and a fake connector whose reader dies
without a close frame, so the same mistake cannot pass again.

Planning also found that the situation is larger than the spec's table: the policy
for each venue is defined **seven times in two modules**, one existing test asserts
the broken value as correct, and the archive already holds **about 24,800 objects under keys
that are wrong** (24,589 at the dry-run, 24,825 and 487 MB minutes later, two more every
minute) — those at the bucket root where no reader looks, and 12,850 at the right prefix
with no symbol in the key — which have to be moved rather than abandoned.

## What planning measured

**Seven `VenuePolicy(...)` definitions in two files.** `connectors/session.py`
holds `BINANCE`, `BYBIT`, `OKX`, `HYPERCORE`; `connectors/venue.py` holds
`BINANCE_POLICY`, `BYBIT_POLICY`, `OKX_POLICY`. The live daemon reads the second set.
They differ: Binance has `stream_lifetime_ns` and no idle timeout in the first and the
reverse in the second; Bybit is 60.0 s against 60.7 s, OKX 30.0 s against 30.9 s, and OKX's ping interval 15 s
against 20 s.
`connectors/__init__.py` re-exports the second set, so removing it touches that too.

**A test asserts the defect.** `tests/unit/connectors/test_venue_connector.py ::
TestVenuePolicies::test_binance_policy` requires `idle_timeout_ns == 24 hours`. It is
green, and it is the reason nothing noticed. The two neighbours pin venue.py's
60.7 s and 30.9 s the same way, and `test_stream_session_policies.py` builds its
fakes from the same constants.

**The silence limit can be grounded in the archive, so it is.** Inter-frame gaps
from the raw archive:

| series | window | frames per minute | longest gap |
|---|---|---|---|
| Bybit BTCUSDT | last 360 complete minutes | min 43, median 352 | **22.2 s** (then 22.0, 18.8) |
| Binance SOLUSDT | 309 sampled minutes, 09-20 to 09-25 | min 30, median 135 | **11.2 s** intra-minute |

One larger figure was found and **excluded with its reason**: a 64.1 s gap beginning
10:54:50. The `ingest-bybit` container started at 10:55:50 — it is the restart made
that morning to repair the network, not a quiet market. A default derived from it
would have been a number measured from our own outage.

**Log volume, steady state, measured over 60 s on 2026-10-02:**

| service | bytes / min | lines / min | MB / day |
|---|---|---|---|
| ingest-binance | 152,511 | 1,292 | 219.6 |
| ingest-binance-eth | 88,148 | 760 | 126.9 |
| ingest-binance-sol | 63,384 | 536 | 91.3 |
| ingest-bybit | 576,722 | 3,216 | 830.5 |
| ingest-okx | 57,152 | 300 | 82.3 |

OKX's 300 lines a minute are the silence warning alone: five a second, for a
connection that has never opened. Together about 1.35 GB a day, and no service
carries a log cap.

**Both venues' rejections were captured live**, so the tests pin real frames:

    OKX    {"event":"error","msg":"Subscribe failed, wrong URL or channel:trades,
            instId:trades.BTC-USDT-SWAP doesn't exist. Please use the correct URL…"}
    Bybit  {"success":false,"ret_msg":"error:handler not found,topic:publicTrade.NOTASYMBOL",
            "conn_id":"…","req_id":"","op":"subscribe"}

For Binance no rejection frame was ever observed: the repository's own comment records
that an upper-case stream name "connects and delivers nothing". With no frame to read,
silence is its only signal — one more reason silence needs a limit of its own.

**What the archive holds, dry-run over the S3 API:**

| venue | at `<venue>/raw/cex/<venue>/` (misplaced) | at `raw/cex/<venue>/` (right place, wrong keying) | clashes if re-keyed |
|---|---|---|---|
| binance | 2,897 (25.0 MB) | 12,850 | 0 |
| bybit | 8,842 (336.7 MB) | 0 | 0 |
| okx | 0 | 0 | 0 |

Sampled objects each held **one** symbol: `09/20 12:00` 467 frames all
`ethusdt@aggtrade`, `09/23 09:30` 430 all `btcusdt@aggtrade`, `09/25 15:00` 235 all
`solusdt@aggtrade`. Three writers grew the archive by one object a minute.

**Dead code at the seam.** `ingest_main._connector_for_venue` builds streams from the
literal `"placeholder"` and returns a subscribe message nothing reads. It is the
shape the real wiring was copied from and it carries the same `trades.` prefix.

**Tooling.** `moto` is not installed, so the migration needs a hand-written fake S3
client, as `ReplayTransport` and `FakeClock` are for the socket and the clock.
PyYAML 6.0.3 is, so the compose test can read the file as data.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new. `boto3` and `websockets` are already used; a fake
S3 client is thirty lines and a dependency for it would be a supply-chain cost for a
dictionary.

**Storage**: the S3-compatible bucket (`raw/cex/...`); no Iceberg table changes.

**Testing**: pytest, `@pytest.mark.trace("REQ-WP-078")`; unit-only, no network.
Live behaviour is checked by hand and recorded in the implement outcome note, with
the date, because CI has no network.

**Target Platform**: `src/channelflow/{connectors,pipeline}`,
`tools/record`, `docker-compose.yml`, `.env.example`, `docs/deployment.md`

**Project Type**: single project

**Performance Goals**: none. The change reduces work: fewer log lines per trade.

**Constraints**: the ingest loop is one thread polling every 200 ms; anything added
to `StreamSession.tick` runs there and must not block.

**Scale/Scope**: five ingest processes, three connectors, about 24,800 objects to move, 487 MB at the last count and growing until the fix lands.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | How this design satisfies it |
|---|---|
| **I. No look-ahead** | Untouched. Nothing here reads data by time. |
| **II. Time is not one thing** | The archive key's minute is **receipt time**, as it is today and as `key_for`'s docstring says; the migration preserves it and does not re-derive a minute from an event time. |
| **III. History is immutable** | Archive objects are replaced by `store.put`, which is how the earlier overwrite happened. Migration **copies, verifies and only then removes**, and refuses an object it cannot attribute, so no object is replaced by a different one. |
| **VII. Live and replay are the same code** | `alive` is part of the protocol every connector and every test fake implements, so the session's reconnect path is the one a replay exercises with a fake. No live-only branch. |
| **VIII. Connectors share one interface** | The interface is *extended* (`alive`), on all three connectors and every fake at once, and `test_protocol_has_required_methods` is updated rather than bypassed. |
| **X. Thresholds are configuration** | Silence limit, backoff ceiling and log caps are each configuration with a default and a written basis; none is a constant inside a method. |
| **XII. Correctness precedes performance** | The log is bounded as an operational matter, after the connection and the archive are right. |
| **XIV. Everything is traceable** | Every new file carries `# @trace: REQ-WP-078`, every test the marker. |

No violations. Complexity Tracking is empty and omitted.

## Project Structure

### Documentation (this feature)

```text
specs/123-ingest-resilience/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── connector.md     # VenueConnector, StreamSession, rejection()
│   ├── archive.md       # key layout, FrameArchive, the re-key tool
│   └── logging.md       # what logs at which level; the compose cap
├── checklists/requirements.md
└── spec.md
```

### Source Code (repository root)

```text
src/channelflow/
├── connectors/
│   ├── session.py            # policies' single home; max_silence_ns; tick(); logging
│   ├── venue.py              # registry only: url, subscribe, policy; rejection()
│   ├── websocket.py          # WebsocketTransport.alive; log why _run ended
│   ├── binance/connector.py  # alive
│   ├── bybit/connector.py    # alive; log levels; rejection frames
│   └── okx/connector.py      # alive; log why the reader ended; rejection frames
└── pipeline/
    ├── archive.py            # FrameArchive(symbol=...); key_for; log levels
    ├── ingest.py             # drop _check_silence; log levels
    ├── ingest_main.py        # build_daemon via the registry; logging in main()
    └── archive_rekey.py      # NEW: the migration, dry-run by default
src/channelflow/bars/builder.py   # log levels

tools/record/parity_capture.py   # --symbol; prefix raw/cex/<venue>/<symbol>/

tests/unit/
├── connectors/test_policies_single_home.py     # NEW
├── connectors/test_rejection_frames.py         # NEW
├── pipeline/test_session_reconnect.py          # NEW: dead reader, silence, lifetime, backoff
├── pipeline/test_build_daemon_seams.py         # NEW: OKX wiring, archive key, two symbols
├── pipeline/test_ingest_logging.py             # NEW: nothing at INFO per step; once on entry/exit
├── pipeline/test_archive_rekey.py              # NEW: FakeS3, attribution, refusal, verify-then-delete
└── deploy/test_compose_logging.py              # NEW
tests/mutations/{session,archive,ingest}.toml   # extended for the new behaviour

docker-compose.yml  .env.example  docs/deployment.md
```

**Structure Decision**: `session.py` stays the home of venue policies. It is where
the measurements are written down (the 60.7 s and 30.9 s observations are in its
docstring) and where the Binance lifetime was originally right. `venue.py` becomes
what its docstring says it is — the registry — and imports from it. The reverse
would have moved measured values into a file whose job is wiring.

## Key decisions

### The connector exposes `alive`; the session polls it

`VenueConnector` gains a read-only `alive` property: the reader is running. The
session's `tick` already runs every 200 ms and is where reconnect decisions live, so
polling fits it. A callback (`on_end(reason)`) was rejected: it fires on the reader's
own thread into code that is not thread-safe, and the value it adds — the reason — is
already logged by the reader at the moment it ends. **The fact is polled; the cause is
logged where it is known.**

### Reconnect on three grounds, for every venue

`tick` reconnects when (1) the stream lifetime has elapsed, (2) the connector is not
`alive`, (3) nothing has arrived for the venue's `max_silence_ns`. The old gate
`not announces_close` on silence is removed: it encoded a belief about what a venue
does when it gives up, and Binance and OKX did something else. `announces_close`
stays as documentation of what was measured; behaviour no longer depends on it.

### Silence is its own field, defaulting to 60 s on the three live venues

`VenuePolicy.max_silence_ns`: how long **this system** tolerates a silent venue. It is
distinct from `idle_timeout_ns`, which is how long the **venue** tolerates a silent
client. The default is **60 s** on Binance, Bybit and OKX: 2.7× the longest real gap
measured (22.2 s) and 5.4× the longest on the thinnest symbol (11.2 s). It is a
starting point with a basis, not a derivation: a quieter symbol would need a longer
one, which is what the override is for. Override:
`CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS`. HyperCore has no live connector; its policy
keeps the old behaviour by falling back to `idle_timeout_ns` when `max_silence_ns` is
unset.

A known limit, stated: silence is measured over *any* inbound frame, and on Bybit and
OKX a pong is one. A subscription the venue has rejected while pongs still arrive is
therefore not silent. That case is covered by the rejection log (FR-003), not by this.

### Backoff is capped exponential, inside the session

Consecutive failed attempts space themselves `min_connect_interval × 2ⁿ`, capped at
60 s (`max_connect_backoff_ns` on the policy). A venue that refuses every connection is
not hammered at one per second, and the logging follows the same count: a WARNING on
attempts 1, 2, 4, 8…, an INFO on recovery stating how many it took. `_reconnect` also
**catches a failed `connect()`**: Binance's raises `NotConnected`, which today would
leave `tick` and end the daemon from inside a reconnect.

### Each venue's endpoint and subscription live in the registry the daemon reads

`VenueConfig` gains `url` and `subscribe_message(symbols)`, the latter taking
**instruments** (`BTC-USDT-SWAP`), not stream names (`trades.BTC-USDT-SWAP`) — the
confusion that put the prefix into OKX's `instId`. `build_daemon` loses its per-venue
`if/elif` for URLs; Binance keeps its one branch because it subscribes by URL. The dead
`_connector_for_venue` is deleted. The test reads `_url` and `_subscribe_msg` off the
connector **the daemon built**, which is the only place this mistake was visible.

### The archive key carries the symbol

`raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz`. `FrameArchive` takes
`symbol`; `build_daemon` passes the bucket path unchanged (`raw/cex`) and no longer
prefixes the venue. A symbol that is empty or contains `/` is refused at
construction: a slash would nest, and the key would stop meaning what its parts say.

### The migration is its own tool, in `src/`, dry-run by default

`src/channelflow/pipeline/archive_rekey.py`, run as `python -m channelflow.pipeline.archive_rekey`.
It lives in `src/` and not `tools/` because **the application image copies `src/` only**
(`Dockerfile`: `COPY src/ ./src/`, and `.dockerignore` excludes the rest) and the tool must
run where the S3 endpoint resolves — inside the compose network. `maintenance_main.py` is
the precedent: operational code that the `maintenance` service and `make compact` both run.
A first draft put it in `tools/`, which would have failed on the first
`docker compose exec`. It reads each object, attributes it to a symbol **from its
own frames** (Binance `stream`, Bybit `topic`, OKX `arg.instId`; a frame carrying none,
such as a pong or an ack, is ignored for attribution), and moves it only if exactly one
symbol appears. The move is `copy_object`, then a `head_object` comparison of size and
ETag against the source, and only then `delete_object`. It refuses — and prints why —
an object with several symbols, none, a destination that already holds different
bytes, or a key that parses as neither old layout. Idempotent: a second run finds
nothing to do. `--apply` is required to change anything.

### Logging is configured in `main()`, and demoted at the source

The per-trade, per-frame and per-step lines go to DEBUG where they are written
(`builder.py` ×4, `ingest.py` ×1, `archive.py` ×3, the Bybit connector's per-frame
pair). `logging.basicConfig` moves out of module import into `main()`, level from
`CHANNELFLOW_LOG_LEVEL` (default INFO): an import that reconfigures the root logger
is a side effect every test importing the module inherits. Events stay at INFO or
above: connect, close, reconnect, recovery.

### Compose caps every service, by configuration

A shared `x-logging` block, `max-size: ${CHANNELFLOW_LOG_MAX_SIZE:-20m}` and
`max-file: ${CHANNELFLOW_LOG_MAX_FILE:-3}`, applied to every service. 60 MB per service
holds days at the expected post-fix rate and rotates every 35 minutes at the pre-fix
rate of the noisiest, which is the point of a cap. The test reads the file as YAML and
fails for a service without one.

## What is deliberately not done

- **Bucket versioning.** It would have preserved the overwritten frames, at storage
  cost and with its own retention question. With the symbol in the key, an overwrite
  now happens only when one process restarts within a minute it had already written, a
  smaller exposure than the one repaired. Named in the outcome note as a decision still
  to take, not decided here.
- **Metrics.** Reconnects and silence are log events with a reason, as the spec says.
- **A rejection reader for Binance.** There is no frame to read; its failure mode is
  silence and is handled as silence.

## Phases

- **Phase 0** — `research.md`: the ten decisions above, each with what was rejected.
- **Phase 1** — `data-model.md`, three contracts, `quickstart.md`.
- **Phase 2** — `/speckit-tasks`, not this command.
