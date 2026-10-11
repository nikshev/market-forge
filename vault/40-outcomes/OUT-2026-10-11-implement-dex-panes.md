---
id: OUT-2026-10-11-implement-dex-panes
step: implement
records: [REQ-WP-099]
commit: null
---

## What was done

Implemented [[REQ-WP-099]] (spec 151) as far as the repository goes; status `tested` until the deployed run.

- `connectors/hyperevm/rpc.py`: a JSON-RPC client for HyperEVM and the three reads the collector needs (head, swap logs of some pools,
  a pool's liquidity/price/fee). A rate limit inside an HTTP 200 is a rate limit; a range over the node's 1000 blocks is
  refused before it is sent.
- `dex/hyperevm_pools.py`: the two pools, pinned from [[REQ-WP-058]]'s measurement (Uniswap v3 and Algebra Integral), the
  liquidity pool, and the series the panes sit on (Bybit `HYPEUSDT`).
- `dex/hyperevm_collect.py` + `pipeline/dex_main.py`: the collector. Cursor per block, pieces of at most 1000 blocks and five
  per poll, a failed piece moves nothing, a restart resumes after the last stored block, a log of a block already stored is
  dropped, a log that cannot be read is counted and skipped. One `dex_state` row per pool per poll **only when the swaps are
  caught up**, which is what the worker reads as "the collector was listening".
- `features/dex_values.py` + `pipeline/context_pass.py`: the two features at each final bar's close for the HYPE series, as of
  the close (a swap counts only if its block time **and** the time it was stored are at or before it).
- `tables/dex_swaps.py` gained `ingest_time_ns` (a swap is knowable only once stored); `tables/dex_state.py` gained
  `reading_row` (a contract read, graded `partial_ticks`, which `dex_active_liquidity` accepts and a depth traversal refuses).
- `tools/panes`: a market with no registered pool says "no DEX pool is registered for this asset"; the pool market says
  whether the collector was listening.
- Compose: `ingest-bybit-hype` and `context-hyperevm`; `.env.example`, Prometheus, `docs/deployment.md`.
- Mutation sweeps: `connectors_hyperevm_rpc` (12), `dex_collect` (16), `dex_values` (10, three equivalent by design), `context_pass`
  (+4), `panes_classify` (3 replaced); survivors reasoned.

## Evidence

**RED first**: `test_rpc.py`, `test_hyperevm_pools.py`, `test_hyperevm_collect.py` and `test_dex_values.py` failed at import
(nothing existed); `test_context_pass_dex.py` had four tests red (the four that expect a written row); the panes tests
failed on the new states. **GREEN**: the same files, plus the deploy, docs and sources suites; lint and type check clean.

A recorded `eth_getLogs` answer (19 swaps from both pools over 81 blocks, 2026-10-11) is the fixture
(`tests/fixtures/dex/hyperevm_getlogs.json`); the expectations are computed from its hex words independently of the decoder.

## What was decided / found along the way

- **The node dates the logs** (`blockTimestamp`), so the first design's block request per swap is not needed. The collector
  refuses a log without one rather than date it by our clock.
- **The public node rate limits inside a 200**: found by probing, then built into the client and a test.
- **Adding `HYPEUSDT` to the series list changes Bybit's collector too** (derivatives, liquidations and book for HYPE): the
  tests that count symbols were updated with the reason beside the number.
- The mutation sweep found that the liveness of the collector (a failed poll counts as a success) was not tested; it is now.

- **The first deployed run found a pane with no producer**: Bybit `HYPEUSDT` is in no consensus group, so its venue-basis
  read answered HTTP 404 and the report said `no-producer`. A second HYPE market, OKX `HYPE-USDT-SWAP`, was added through the
  same series, ingest and registry path as [[REQ-WP-098]], and the two form the HYPE perpetual group.

## What is still open

- Deployment: the ingest, the collector, then the worker; the acceptance reads are measurements of that run.
- Whether a second HYPE market should carry the panes.
