---
id: OUT-2026-10-11-implement-consensus-producer
step: implement
records: [REQ-WP-096]
commit: null
---

## What was done

Implemented [[REQ-WP-096]] (spec 148) as far as the repository goes. Status is `tested`: the venue-basis pane enabled
for Bybit and OKX BTC and the Binance read answering its refusal (SC-004) are measurements of the deployment.

- **`crossvenue/deployment.py`**: the deployment's markets, the asset each stands for and its market type, the
  registry built from them (a CEX market is a representation `0:cex:<venue>:<symbol>`, identified as a market and
  not a token), and the groups consensus is taken over -- per asset and market type, never blended.
- **`pipeline/consensus_pass.py`**: the worker's pass. One row per minute close, because every bar close is one;
  the library's own `consensus_mid`, its refusals stored with their reason; idempotent from a watermark per symbol.
- Wired into the worker beside the context features; the `consensus` table joins the maintenance service.
- **Mutation sweeps**: two files, 23 mutations, survivors reasoned.

## Evidence

**RED first**: the test file was written and run before the modules existed:

    ModuleNotFoundError: No module named 'channelflow.crossvenue.deployment'
    1 error during collection

**GREEN**: 21 tests; they include the API's own reads over what the pass wrote -- `select_venue_basis` for both
perpetual venues equals `10000 * (mid / consensus - 1)` computed from the stored mids, and the Binance spot read
returns the stored refusal and no basis.

## What was decided / found along the way

- **The API asks for the consensus by the viewed venue's symbol, not by a canonical asset** (`asset=symbol` in the
  routes, with a comment that the two "are the same string" for every market served -- not true for OKX, whose
  symbol is `BTC-USDT-SWAP`). So the perpetual BTC consensus is stored under *both* `BTCUSDT` and `BTC-USDT-SWAP`,
  identical in value, and either chart finds it. Changing the API to map a symbol to an asset would have been the
  cleaner design and a wider change; this keeps the readers as they are.
- **The pass advances over a close only once every live venue's data is known to be complete up to it.** Completeness
  is the storage time of a venue's newest quote (a minute's quote is written when the minute ends), not its exchange
  time -- the first version used exchange time and so could never compute the last minute it had data for. A venue
  that is more than ten minutes behind the freshest is no longer waited for; its stale quote is excluded by the
  library's own rule.
- **A 15-second staleness bound, not the library's 5**: a quote per minute is the last message before the boundary,
  which on a quiet book can precede it by a few seconds.
- **Binance spot has one venue**, so its group is refused every minute with the library's own reason ("only 1
  venue(s) could contribute...") and the pane says so. A second spot venue is the owner's option, not built.

## What is still open

- The worker has not been rebuilt with this pass; after it is, the first pass backfills a consensus for every minute
  with quotes (a few thousand rows, one commit).
- The registry is a short list in code; adding a market is one line there and one stream in `context/sources.py`.
