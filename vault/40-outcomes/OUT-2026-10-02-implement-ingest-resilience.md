---
id: OUT-2026-10-02-implement-ingest-resilience
step: implement
records: [REQ-WP-078]
commit: null
---

## What was done

Seven measured defects, closed in the order the tasks gave, each with the test written before the
code that satisfies it. The suite is red between the test and the code, so a red commit is
impossible by design ([[REQ-WP-078]]'s ladder note in `CLAUDE.md`); what proves the order is the
RED output below, captured before any source change in each phase.

**RED, as run** (the lines that matter, from the runs before each phase's source change):

- Archive and `build_daemon` seams: `13 failed, 1 passed`. `FrameArchive.__init__() got an
  unexpected keyword argument 'symbol'`; `okx/raw/cex/okx/2026/09/21/1413.jsonl.gz` — the venue
  at the bucket root and again after `raw/cex`, which is defect 4 reproduced by a test.
- Re-key tool and parity capture: `ImportError: cannot import name 'archive_rekey'`.
- Policies: `VenuePolicy has no attribute 'max_silence_ns'`; `binance is defined with different
  values in: …BINANCE_POLICY; …session.BINANCE`; `assert None == 24h` (Binance's stream
  lifetime had been moved into the wrong field).
- Reconnect: `assert 0 == 1` on `connector.closed` for every venue — a connection whose reader
  died was never reopened.
- **Found live, not by any test.** The first live reconnect proof killed the Bybit daemon: the
  client ping went to the socket the dead reader had left behind and raised
  `ConnectionClosedError` out of `StreamSession.tick`. Every fake in the suite had a `send` that
  worked. Five new tests failed for the right reasons (`ConnectionError: the socket has gone`
  out of `tick`; `_ws` still the previous socket after `connect()`), then passed after the fix
  (commit d4f91ab).

**Before and after, measured on the running stack** (60 s windows, containers recreated by
`docker compose up -d --build`):

| service | before | after |
|---|---|---|
| ingest-binance | 329,185 B/min | 133 B/min |
| ingest-binance-eth | 404,890 B/min | 134 B/min |
| ingest-binance-sol | 66,350 B/min | 133 B/min |
| ingest-bybit | 782,037 B/min | 131 B/min |
| ingest-okx | 56,776 B/min | 136 B/min |

The ceiling SC-004 states is 6,944 B/min; the worst service is 136. Compose now caps every
service's log at 20 MB × 3 files (`CHANNELFLOW_LOG_MAX_SIZE`, `CHANNELFLOW_LOG_MAX_FILE`), proven by a
test that reads the file.

**Archive re-key, applied.** 24,987 objects moved to `raw/cex/<venue>/<symbol>/…`, each copied,
compared by size and ETag, then deleted; a second apply moved 0 and found 0 refused. The extent
of what the overwrite cost, per symbol (the span is the venue's first archived object to its
last):

| symbol | minutes held | minutes held only by another symbol | minutes with no object |
|---|---|---|---|
| binance BTCUSDT | 6,099 | 9,878 | 5,963 |
| binance ETHUSDT | 4,414 | 11,563 | 5,963 |
| binance SOLUSDT | 5,526 | 10,451 | 5,963 |
| bybit BTCUSDT | 9,072 | 0 | 3 |

"Held only by another symbol" is an upper bound on what was overwritten, not a count of it: in
those minutes the symbol's frames were overwritten *or* its process was not running, and the
archive cannot say which. The first version of this report called that column "missing" and
printed 17,526 for ETH, which read as an overwrite count and was not; it is split into the two
columns above, and the bars table (which has a bar for every minute a process ran) is where the
two are told apart.

**Live proofs.**

- OKX connects and delivers: 17 OKX rows in `bars` (newest closing 15:53 UTC when read at 16:01,
  the sink flushes in batches) and 22 objects under `raw/cex/okx/BTC-USDT-SWAP/` in the hour
  before the last check, each holding 800-2,000 frames.
- Archive layout, one hour after the recreate: 59 / 60 / 59 / 59 objects for Binance BTC / ETH /
  SOL and Bybit BTC — one per minute per symbol — and **0** objects written outside `raw/cex/`.
- Reconnect, by dropping only tcp/443 in the Bybit container's network namespace for 140 s
  (`scratchpad/live_reconnect.sh`; Postgres and MinIO untouched): the container's restart count
  stayed 0. The log shows one WARNING on entry (`bybit connection down: the connector's reader
  has ended`), `still down after 2 attempts` and `after 4 attempts` at the backoff's steps, a
  `could not open … Network is unreachable` per failed open, and one INFO on recovery (`recovered
  after 4 attempt(s), down for 92.5 s`) when the first frame arrived. The minute object
  the outage began in (`1557`) was archived with the 207 frames received before the block; the
  `1559` holds the 81 frames after recovery, and no object exists for the minutes between, so the
  outage is visible in the archive as missing minutes. The earlier run of the same
  script is the one that crashed.

**Mutation sweep, all seven specs:** archive 14, archive_rekey 11, session 33, subscribing 11,
venue_rejection 6, ingest_main 10, ingest 13 — **98 caught, 0 survived.** Real gaps the sweeps
found along the way: two specs did not run the new test files at all (`archive.toml`,
`session.toml`), an unreachable guard in the re-key tool survived and was deleted rather than
excused, `main()` could have stopped calling `configure_logging` with nothing failing, and
clearing a replacement reader's socket survived until a test started one reader beside another.

## What was decided

- **A ping that fails is a warning, not an error, and is not retried before its interval.** The
  reader ending is what reconnects; the ping is only a way of finding the socket gone sooner.
  The session stamps the ping clock before sending, so a persistent failure costs one line per
  interval, not five a second.
- **A connector forgets its socket twice**: when `connect()` begins, and when its own reader
  ends — but only if the socket is still its own, because a reconnect starts the new reader
  while the old one may still be finishing.
- **The silence limit is 60 s by default**, from the longest real gaps in the archive (22.2 s
  Bybit BTCUSDT, 11.2 s SOLUSDT; a 64.1 s gap was this project's own restart and is excluded).
  Configurable through `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS`.
- **Objects that hold several symbols are refused and left in place**, not split. None were found
  in the live bucket (`refused 0`).

## What is still open

- **The overwritten minutes are not recoverable from the archive.** Their extent is stated, not
  repaired. Bars and channels were never affected.
- **The websockets library logs one ERROR traceback per outage** (`keepalive ping failed`) before
  the project's own WARNING. One per outage, not per second; left alone rather than silencing a
  third-party logger, and noted for anyone who sees it.
- `channelflow.tables.bars` logs `BarSink.flush called` at INFO once per closed bar (about one
  line a minute per service, inside the 6,944 B/min ceiling at 136 B/min). Demoting it would be
  a one-word change; it was left because it is the only line that says the sink is alive.
- Bucket versioning and reconnect metrics are out of scope by the spec (PRD §33's reconnect and
  stale-feed counts stay log events).
- **Process mistakes worth recording.** The FakeS3 tests were written alongside the archive code
  rather than strictly before it. And one of this work's own early claims — that the OKX frame
  shape was "captured live" — was corrected during planning rather than left standing.
