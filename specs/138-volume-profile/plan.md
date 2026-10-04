# Implementation Plan: A volume profile beside the price axis

**Branch**: `138-volume-profile` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

Four phases, the first deployed as soon as it passes so the data starts to accumulate: **A** `volume/bins.py` (a pure
`PriceBinBuilder`, 5-minute blocks, completeness from trade ids), `tables/volume_bins.py` (schema, sink, reader) and the ingest wiring;
**B** `profile.from_bins` reusing POC and value-area code, and a repository method; **C** the API route; **D** the web: a series primitive,
a profile fetch, a window selector and a coverage line. Nothing is backfilled.

## What planning measured

- `profile.build` bins by `floor((price - anchor) / width)` and its tail (`_point_of_control`, `_value_area`) takes `Bin`s; a
  `from_bins` can aggregate rows to `Bin`s and call the same tail, so the two cannot disagree.
- `BarBuilder` owns its own windows and watermark; `ingest.IngestDaemon._consume` feeds it; `ingest_main` builds the sink and passes
  `flush_bars` / `bars_pending`. A second builder fed at the same call changes none of that.
- Bin counts: BTCUSDT moves about 0.2% in five minutes; at a 2 bps width that is about ten bins a block, so about 3,000 rows a day
  per symbol.
- `lightweight-charts` 4.2.3 typings: `ISeriesApi.attachPrimitive`, `ISeriesPrimitive`, `ISeriesPrimitivePaneView.renderer()`,
  `ISeriesPrimitivePaneRenderer.draw(target)`; `priceToCoordinate` on the series.
- The repository protocol and its in-memory and lakehouse implementations (`repositories.py`, `lakehouse_repository.py`) are where a
  new read goes.

## Decisions, and what each rejected

**D1. Aggregate at ingest into 5-minute blocks of price bins.** Rejected: storing every trade (hundreds of millions of rows);
a profile from bars (forbidden by §14.1); one-minute blocks (five times the rows for nothing a 4h+ profile can show).

**D2. A separate pure builder**, not a change to `BarBuilder`: its windows and watermark are mirrored, its tests are untouched, and
bin collection can be switched off by not constructing it. Rejected: adding bins to `Bar` (a schema change to the central table).

**D3. The profile is computed on request from the bins**, as of an instant, point-in-time by the table's event-time column (the
block's close). Rejected: precomputed snapshots (rows every five minutes per window, the same data three times over, for a request
that is cheap).

**D4. Width per symbol: an environment override, else derived from the first trade** (2 bps, rounded to 1-2-5) and **written on every
row**. A profile uses the latest width and says if rows were left out. Rejected: a global constant (BTC and SOL differ by three orders
of magnitude); a geometric grid (breaks the arithmetic-bin reuse of `VolumeProfile`).

**D5. Incomplete blocks are dropped, not flagged**, as for flow rows: a wrong profile is worse than a gap.

**D6. A series primitive draws it.** Rejected: price lines carrying the width in their titles (the existing, never-fed approach: reads as
labels); a DOM overlay (re-positioned on every pan, zoom and autoscale).

**D7. Coverage is part of the response and of the picture.** A 24h profile from three hours of data says three hours.

## Tests (written first)

pytest, `@pytest.mark.trace("REQ-WP-089")`: the builder (SC-001; boundary; late trade; bin-edge price; unknown; order within the grace
period; id-span completeness for a flagged venue; counters), the width rule, the table's sink and reader (point-in-time, one width),
`from_bins` equals `build` (SC-002), no look-ahead (SC-003), coverage (SC-004), the API route (200, 404, 422, `at_ns`), the ingest
wiring (a fake session's trades reach the sink). vitest, with the library replaced: the primitive's renderer draws bars at
`priceToCoordinate(low..high)` in the right colours, nothing with the layer off, the selector, the coverage text. Mutation specs for the
builder and `from_bins`. Python: the screenshots exist and the modules trace.

## Constitution Check

I: a block is whole and closed before it is used; a profile as of `t` uses blocks closed at or before `t`. III: blocks are appended
once and never amended. VII: one builder for live and a later replay. X: the width and the block length are configuration with
defaults. XIV: traced. No violations.

## Risks

- The first hours have a thin profile; the coverage line is the answer, not a hidden limitation.
- Reading the bins table whole per request grows with the table; the maintenance job exists and the window bounds the use; revisit if it
  is slow.
- An ingest restart loses the block in progress; for Binance the id check drops it, for others it is a partial block (stated).

## Project Structure

```text
src/channelflow/volume/bins.py            PriceBinBuilder, BinBlock, nice_bin_width (new, pure)
src/channelflow/volume/profile.py         from_bins reusing the POC and value-area tail
src/channelflow/tables/volume_bins.py     schema, sink, reader (new)
src/channelflow/pipeline/ingest.py        the builder fed beside the bar builder
src/channelflow/pipeline/ingest_main.py   wiring, width configuration, flush
src/channelflow/api/                      repository read, route, schema
apps/web/src/profilePrimitive.ts          the series primitive (new)
apps/web/src/api.ts, types.ts, Chart.tsx, App.tsx   fetch, draw, selector, coverage
```
