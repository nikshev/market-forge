# Implementation Plan: A second spot venue

**Spec**: [spec.md](spec.md) | **Requirement**: [[REQ-WP-098]]

## Summary

Four small changes on paths that already exist. (1) Three compose ingest services. (2) `context/sources.py` gets one
`SERIES` list from which the perpetual mapping and each venue's book symbols derive. (3) `context/book.py` decides a
book's market type and size conversion per instrument. (4) `crossvenue/deployment.py` lists the OKX spot markets.

## Design decisions, with what was rejected

1. **`SERIES` is the one list** of what the deployment ingests, with each market's type; `PERPETUALS` stays an explicit
   mapping (a spot series is shown a *named* perpetual) and a test checks every mapped perpetual is a polled symbol. Rejected: deriving the
   mapping by string rules (`BTC-USDT` -> `BTC-USDT-SWAP`): a convention in code is the shortcut ADR-038 refuses.
2. **Kind by instrument, not by venue**: OKX symbols ending `-SWAP` are perpetuals (contracts), others spot (base units); the rule lives
   beside `okx_market_type`'s own, which already makes the same decision for trades.
3. **One book subscription for four OKX instruments** (three spot, one swap): one connection, one `MinuteBook` each.
4. **No change to the consensus maths or the API**: the registry (`deployment.py`) gains three markets; the aliases make the rows findable.

## Project Structure

Touched: `context/sources.py`, `context/book.py`, `pipeline/context_main.py` (book symbols distinct from derivative symbols),
`crossvenue/deployment.py`, `docker-compose.yml` (3 ingest services), `.env.example`, `docs/deployment.md`.

## Phases

1. Tests (sources, book kind/size rule, deployment, context_main). 2. Implementation. 3. Mutations. 4. Start the three ingests (`up -d --no-deps`), rebuild the OKX collector, then the worker. 5. Panes report.
