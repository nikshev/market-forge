# Implementation Plan: The order-flow panes and the venue quotes are fed by a top-of-book subscription

**Branch**: `147-book-subscription` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: `specs/147-book-subscription/spec.md`; [[ADR-070]]. Builds on spec 145's runtime and spec 146's `context/streams.py`.

## Summary

A book stream per venue feeds a per-symbol `MinuteBook` that wraps the existing `OFITracker` and `BookService`, finalises each minute in event time, and emits a `book_minutes` row plus a `quotes` row. The worker evaluates `ofi_1m` and `depth_imbalance_10` at each bar close from the summary of the last closed minute.

## Technical Context

Python 3.12; the existing transport and `StreamSession`; `Decimal` arithmetic throughout (the existing book and OFI code is Decimal). Recorded frames per venue as fixtures; a scripted-sequence generator for the minute-boundary tests.

## Constitution Check

I: a minute is finalised from frames before its boundary; the worker reads summaries with `close <= bar close`. II: venue event time and receive time stored apart. III/XII: the sampling is stated in the registration. XIV: traces.

## Project Structure

```text
src/channelflow/connectors/{binance,bybit,okx}/normalize.py   # book snapshot normalisers (exist for Binance depth_snapshot and Bybit order_book_message; OKX gains books5/books); crossed/empty refused
src/channelflow/context/minute_book.py                        # MinuteBook: feed(snapshot) -> finalised minutes; reset() at reconnect
src/channelflow/tables/book_minutes.py                        # schema, to_row, BookMinuteSink, table_for; quotes via existing tables/quotes.py
src/channelflow/features/context_write.py                     # + book_rows(): ofi_1m, depth_imbalance_10 as of each close
tests/unit/context/test_minute_book.py  tests/unit/tables/test_book_minutes.py  tests/unit/features/test_context_write_book.py
tests/mutations/context_book.toml
```

Touched: `connectors/venue.py` (`CONTEXT_STREAMS`: book entries -- Binance spot for the spot series, Binance futures not used for the series; Bybit linear; OKX), `registry` text of the two features (sampling stated), `pipeline/context_main.py`, maintenance `TABLES`, `docker-compose.yml`, `docs/deployment.md`.

## Design decisions, with what was rejected

1. **Streams**: Binance spot `<symbol>@depth10@1000ms` (ten levels, one frame a second: the lightest honest stream); Bybit `orderbook.50.<symbol>` is deltas after a first snapshot -- Bybit has no ten-level snapshot-only linear stream, so **Bybit uses `orderbook.1`/`orderbook.50` through `BookService`'s delta handling** (the service exists and is tested; this is the one venue that needs it) and OKX `books5` gives five levels: the OKX series' imbalance is therefore `DI_5` unless the plan's measurement finds `books` (400 levels) affordable, and the feature's `source` says which depth each venue used. The per-venue depth is recorded in the outcome note, and `depth_imbalance_10` is written for a venue only when its book has at least ten levels per side (otherwise absent, never a five-level number under a ten-level name).
2. **Interval chosen by measurement**, starting at the venue's slowest snapshot stream; Bybit's `orderbook.50` is 20 ms deltas -- the plan samples `BookService` once per second, not per delta, so OFI increments come from 1 Hz observations on every venue (the same sampling, stated). Rejected: per-event OFI (needs full delta fidelity and is the §11.1 reconstruction this spec excludes).
3. **`MinuteBook` finalises on the first frame of the next minute** using only frames before the boundary; a long silence finalises on the clock tick of the runtime with the same rule (frames before the boundary), so a dead stream still closes its minutes (with count zero).
4. **OFI uses the existing `OFITracker`** over 1 Hz `Observation`s, reset at a reconnect; the window total for the minute and its observation count are stored; zero count writes nothing.
5. **`quotes` rows are written at minute close** from the last valid frame before the boundary (exchange time = that frame's), receive time = when it arrived.
6. **Worker `book_rows`**: as of a bar's close, the latest `book_minutes` row with `minute_close <= close` and `count > 0`, not older than 2 minutes at the close (staleness stated).

## Risks

- **Host load**: five 1 Hz book streams are small; Bybit's 20 ms deltas are the heavy part and are sampled, not stored. Measured before/after (SC-006); if the load is not acceptable the stream is dropped to `orderbook.1` (top of book only: OFI yes, depth imbalance no), recorded as such.
- **OKX depth**: five levels cannot give `DI_10`; stated above.
- **Bybit delta continuity**: `BookService` already handles gaps by requesting a snapshot (resubscribe); a gap resets the tracker and the minute's count says so.

## Phases

1. Fixtures, normalisers, `MinuteBook`, table (tests first). 2. Stream tasks + wiring, measure load. 3. Worker `book_rows` + no-write replay. 4. Deploy; recorded queries.
