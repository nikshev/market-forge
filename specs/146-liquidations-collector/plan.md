# Implementation Plan: The liquidations pane is fed by each venue's liquidation stream

**Branch**: `146-liquidations-collector` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/146-liquidations-collector/spec.md`; [[ADR-070]]. Builds on spec 145's `channelflow.context` runtime.

## Summary

Per-venue liquidation parsers (`connectors/{binance,bybit,okx}/liquidation.py`), a `liquidations` table and sink, a stream task in the collector built on the **existing** `StreamSession`/`WebsocketTransport` (keepalive, silence limit, reconnect already decided and tested there), and a second worker pass `features/context_values.py (pure) and pipeline/context_pass.py (the pass)::liquidation_rows` that evaluates the five liquidation features at every bar close using `derivatives/liquidations.py`.

## Technical Context

Python 3.12; `websockets` through the existing transport; no new dependency. Tests with recorded frames in `tests/fixtures/context/` (one per venue, captured by `tools/record/liquidation_capture.py` which listens until it has seen a frame or a stated timeout -- Binance's stream can be quiet for minutes).

## Constitution Check

I (no look-ahead): events with `event_time <= close`. II: venue time and ingest time stored apart. XIV: traces. All others as spec 145.

## Project Structure

```text
src/channelflow/connectors/binance/liquidation.py   # forceOrder frame -> LiquidationEvent
src/channelflow/connectors/bybit/liquidation.py     # allLiquidation frame -> [LiquidationEvent]
src/channelflow/connectors/okx/liquidation.py       # liquidation-orders frame -> [LiquidationEvent]; contract size -> base units
src/channelflow/tables/liquidations.py              # schema, to_row, LiquidationSink (dedupe by identity), table_for
src/channelflow/context/streams.py                  # shared: a StreamSession task per (venue, kind), frames -> handler, reconnect/silence metrics
tests/unit/connectors/test_liquidation_*.py  tests/unit/tables/test_liquidations.py  tests/unit/pipeline/test_context_pass_liquidations.py
tests/mutations/context_liquidations.toml
```

Touched: `connectors/venue.py` (a `CONTEXT_STREAMS` registry beside `VENUE_REGISTRY`: stream names, URL, subscribe message per venue and kind -- futures hosts differ from the spot trade stream), `context/sources.py`, `pipeline/context_main.py`, `features/context_values.py (pure) and pipeline/context_pass.py (the pass)`, `pipeline/maintenance_main.py`, `docs/deployment.md`.

## Design decisions, with what was rejected

1. **Side of the position, pinned per venue by a recorded frame.** Binance `forceOrder`: the order's side is the closing side (SELL liquidates a long). Bybit `allLiquidation`: the frame's `S` is documented as the position side that was liquidated -- **to be confirmed against the recorded frame and Bybit's documentation before the test is written; the test records which**. OKX: `side`/`posSide`: `posSide=long` with `side=sell` is a long liquidated; net-mode (`posSide=net`) derives from `side`; anything else is `unknown`.
2. **Contract sizes**: OKX reports contracts (`sz`); BTC-USDT-SWAP's `ctVal` is 0.01 BTC and is fetched once from `public/instruments` at start, stored in the collector's config for the symbols it watches; an instrument whose size cannot be fetched refuses its events (never guessed).
3. **Heartbeat is spec 145's state rows**: a window is covered if a polled state exists within each poll interval-and-a-half across it, computed by the worker from `derivatives_state` (no new table). A venue whose derivatives collector is the same process shares fate with its stream, which is exactly the property wanted.
4. **Dedupe on identity at the sink** (venue, symbol, event time, price, qty, side), kept in a bounded set of the last N identities; after a reconnect the venue may replay recent events.
5. **No raw archive of liquidation frames**: events are the data; the frame is tiny and its normal rate low, but the table keeps ingest time, and the parser's recorded fixtures are the reference. Rejected: archiving through `FrameArchive` (a second consumer of a path built for trades).

## Risks

- **Silence is normal for Binance**: the silence limit is a ping/pong liveness, not a data window (the session already distinguishes them); the heartbeat covers the rest.
- **A cascade burst**: sink batches; commits are time-bound.
- **Bybit/OKX schema drift**: the parser refuses a frame with the missing field named and counts it; health reports parse failures.

## Phases

1. Fixtures (record), parsers, table, sink (tests first). 2. Stream task + wiring in the collector. 3. Worker liquidation pass + no-write replay. 4. Deploy with the collector; recorded query for SC-004.
