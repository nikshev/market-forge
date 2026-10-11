# Implementation Plan: The DEX panes get a source

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-099]]

## Summary

Five pieces, each on a path that exists: (1) a JSON-RPC provider for HyperEVM, (2) a pure log-to-swap conversion over the
existing decoder, (3) a collector loop with its own cursor and the existing health server, (4) a worker pass that writes the two
features for the HYPE series, (5) one ingest service and one collector service.

## Design decisions, with what was rejected

1. **The pools are pinned, not discovered.** Their addresses, factories, tokens and decimals are [[REQ-WP-058]]'s measurement and
   live in code (`dex/hyperevm_pools.py`). Rejected: reading `token0()` at start -- three more calls into a node that rate limits
   within seconds, to learn what has been fixed since the pools were deployed.
2. **One `eth_getLogs` for both pools, one request per piece**, `blockTimestamp` from the log. Rejected: `eth_getBlockByNumber`
   per swap (the first design in `tools/record`): it multiplies the requests by the swap count.
3. **Coverage by the poll itself.** Each successful poll stores one `dex_state` row per pool (`liquidity()`, grade `partial_ticks`,
   dated at the block read). A window is evaluated only if every minute of it has a row for every pool -- the rule
   `liquidation_values.covered` already states. Rejected: a heartbeat table (a second place to be wrong).
4. **Active liquidity from the busiest pool**, because the value is not comparable across pools (REQ-WP-063). The pool is a
   pinned fact (`LIQUIDITY_POOL`), with the measurement that chose it beside it.
5. **The series is Bybit `HYPEUSDT`.** The features are keyed by `(venue, symbol)`; the pools price HYPE. One series carries
   the DEX panes: each series costs a worker cycle ([[REQ-WP-098]] measured that). **Amended after the first deployed run:**
   a second HYPE market (OKX `HYPE-USDT-SWAP`) is ingested too, because a series in no consensus group has a venue-basis
   pane with no producer (HTTP 404, not a refusal), and a second venue is what makes the group.
6. **Not stored twice.** The sink drops a swap whose `(chain_id, tx_hash, log_index)` is already known to it; the cursor is
   restored from the table's latest block at start and the first range overlaps by one block.

## Project Structure

New: `connectors/hyperevm/rpc.py`, `dex/hyperevm_pools.py`, `dex/hyperevm_collect.py`, `pipeline/dex_main.py`, `pipeline/dex_pass.py`.
Touched: `context/sources.py` (HYPE series), `pipeline/channel_main.py` (calls the pass), `tools/panes/classify.py`,
`crossvenue/deployment.py` only if the registry test requires it, `docker-compose.yml`, `.env.example`, `docs/deployment.md`.

## Phases

1. Tests: RPC provider, conversion, collector, pass, sources, report, compose. 2. Implementation. 3. Mutations.
4. Gate and commit. 5. Deploy (new services first, worker when the measurement window closes). 6. Report and screenshots.
