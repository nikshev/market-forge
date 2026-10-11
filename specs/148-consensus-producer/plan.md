# Implementation Plan: The venue-basis pane has a consensus

**Branch**: `148-consensus-producer` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/148-consensus-producer/spec.md`; [[ADR-070]]; spec 140's consensus library. Needs spec 147's `quotes`.

## Summary

One worker pass, `crossvenue/consensus_write.py::write_consensus`, reads the `quotes` table once, and for every minute close with quotes computes each (asset, market type) consensus through the existing `consensus_mid`, storing a row per close (refusals included). It is idempotent by a per-(asset, market type) watermark.

## Technical Context

Python 3.12; existing `crossvenue/consensus.py`, `tables/quotes.py`, `tables/consensus.py`, the asset registry the API reads. One table read per pass; computation grouped by minute.

## Constitution Check

I: `consensus_mid` already refuses later quotes; tested by appending. XIV: traces.

## Project Structure

```text
src/channelflow/crossvenue/consensus_write.py       # write_consensus(catalog, registry): the pass
src/channelflow/tables/consensus.py                 # + ConsensusSink / latest_closes() (read the watermark), if absent
tests/unit/crossvenue/test_consensus_write.py       # fixtures: 2 and 3 venues, one venue, stale, later, idempotence, gap
tests/mutations/consensus_write.toml
```

Touched: `pipeline/channel_main.py` (one call after the context features), the asset registry's configuration for the deployment's symbols (if the perpetual BTC symbols are not mapped), `docs/deployment.md`.

## Design decisions, with what was rejected

1. **One row per minute close, not per timeframe**: every timeframe's close is a minute close; the API selects by `bar_close_ns`. Rejected: per-timeframe rows (multiplies storage by the number of timeframes for no new information).
2. **A refusal row is written, including for a gap** (reason from the library, or "no fresh quotes from any venue"), so the pane can say why.
3. **Staleness** is the library's parameter, set to 2 minutes (a minute cadence plus slack), named in `context/sources.py`.
4. **Registry first**: the plan's first task is to confirm the registry maps `bybit BTCUSDT` and `okx BTC-USDT-SWAP` to one asset with market type perp; if it does not, the mapping is added as data with a test, not code.
5. **Watermark** = latest `bar_close_ns` per (asset, market type) in `consensus`; the pass computes closes after it up to the newest quote time of the contributing venues.

## Risks

- **A venue's quotes lag the others** at the pass: the pass stops at the minimum of the contributing venues' newest quote times, so a close is never computed from a partial set because one venue's rows had not landed.
- **Registry gaps** (a symbol with no asset): reported once per pass and skipped, never guessed.

## Phases

1. Registry check and fixtures (tests first). 2. The pass. 3. No-write replay on real quotes once spec 147 has produced a day. 4. Deploy with the worker; recorded reads for SC-004.
