---
id: OUT-2026-10-03-implement-markets-registered
step: implement
records: [REQ-WP-081]
commit: null
---

## What was done

Each ingest process now registers the market it ingests, once, at start-up; `GET /api/v1/markets` lists
five markets where it listed none, and the overview has something on its first screen.

- `VenueConfig.market_type(symbol)` on the registry: binance `spot` (its feed is `stream.binance.com`, the
  spot stream — PRD §26.1's example says "Binance Perp"), bybit `perp`, OKX `perp` for `…-SWAP`, `spot` for
  a pair, and a refusal for anything else rather than a guess.
- `features.unruled_market_row`: the one definition of a market with no rules, used by `add_market` and by
  registration. `pipeline/market_registration.py`: `register_market` (reads first, idempotent),
  `register_softly`, `register_own_market`; called in `ingest_main.main` before `daemon.run()`.
- **`IcebergTable.append` no longer loses a race to create the table** (below).
- A section of `docs/deployment.md`; no change to the page, which already rendered what it was given.

## RED, as run

- Types: `AttributeError: 'VenueConfig' object has no attribute 'market_type'` (11 tests).
- Registration: `ModuleNotFoundError: No module named 'channelflow.pipeline.market_registration'`.
- The table-creation race, threaded: `TableAlreadyExistsError('Table channelflow.cex_trades already exists')`
  for 4 of 5 writers; and, with no threads and the interleaving forced, the same.
- **Green from the start, on purpose:** the overview page with the five-market response (3 tests): the page
  was not changed and the test pins what it renders.

## What the work found

- **A first-start race that would have left four markets in five unlisted.** Looking for a table and
  creating it are two steps, and five daemons restarted together after a deploy take both. Nobody was
  testing that; the five-thread registration test did, by accident, on its first run. It is not specific to
  markets: any first append to any new table (`bars` on a new deployment) could lose it.
- **My own test table had a bug**: `stream.binance.com` is a substring of `fstream.binance.com`, so the
  futures endpoint read as spot. Fixed by matching with the scheme.
- **Two test assumptions were wrong** (decimal columns read back as text), fixed in the tests.
- **The mutation sweep found three behaviours unpinned** (the type per venue — a registration writing `perp`
  for everything passed every first test —, two symbols of one venue, an unreachable catalog); tests added
  after it, and said so in the file. Two spec anchors went stale by formatting and one by an ambiguity;
  repaired.
- **`setup-plan.sh` follows `.specify/feature.json`**, which still named the previous feature; corrected.

## After

`make test` 3215 passed; `make web-test` 277 (30 files); lint, mypy, `web-typecheck`, `web-build` clean; no
existing test edited. Mutation sweeps: `market_registration` 6/6, `market_types` 5/5,
`ingest_main_registration` 1/1, and the lakehouse spec's new case 9/9 — none survived.

**Live, 2026-10-03 17:05 UTC.** The five ingest services were recreated (`--no-deps`); each logged
`registered as a spot|perp market`; `GET /api/v1/markets` (direct and through the web proxy):

    binance BTCUSDT spot · binance ETHUSDT spot · binance SOLUSDT spot · bybit BTCUSDT perp · okx BTC-USDT-SWAP perp

Restarting `ingest-bybit` twice left five entries and one registration line in its log.

## What was decided

- **No integration test.** The markets table has a fixed name and the stack's catalog is the one the API
  reads, so a test against it would write into the live list. The thread test and the forced-interleaving
  test on SQLite carry the concurrency.
- **Status `implemented`.** The live acceptance — five rows on the running stack — is shown above.

## What is still open — and one thing I caused

- **The worker restarted twice at 16:38 UTC, and that was my experiment.** While comparing the old and new
  perf measurements I ran four CPU-burning loops for several minutes (load average near 10). MinIO answered
  a `HeadObject` with **HTTP 503**, which surfaced as `OSError` in the worker's first read of a pass; that
  read is outside the per-series handler, so the process exited and compose restarted it (`restarts=2`).
  It recovered by itself; `resample` was not affected (`restarts=0`, still running from 07:18). It is the
  same shape as the resample exit that [[REQ-WP-079]] recorded: an unguarded first read, now with a second
  cause (a transient storage error, not `NoSuchSnapshot`). Not fixed here; it wants its own requirement.
  The [[REQ-WP-079]] count (`NoSuchSnapshot` in `worker` and `resample`) is still 0.
- The overview still says "ChannelFlow" and every market is unscored.
- `fstream` and OKX's dated futures are not recognised or registered; adding one means a registry entry.
