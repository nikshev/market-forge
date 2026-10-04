# Implementation Plan: CVD and the trade-imbalance features, from bars

**Branch**: `135-trade-flow-features` | **Date**: 2026-10-04 | **Spec**: [spec.md](./spec.md)

## Summary

A pure function `flow_rows(bars)` in `features/flow_bars.py` turns a series' final bars into flow rows (delta, CVD,
normalised delta, slope, acceleration, run id) with run breaks read from the bars. The worker pass calls it for each
`(venue, symbol, timeframe)` after its channel step and writes the rows through a feature sink that reads the latest
row on record first. Six features are registered. The CVD pane draws `cvd_base` and breaks at a `cvd_run` change. No
change to ingest, resample, the bar schema or the API.

## What planning measured

- The bars table has `aggressive_buy_base`, `aggressive_sell_base`, `delta_base`, `trade_count`, `volume_base`,
  `first_trade_id`, `last_trade_id` (`tables/bars.py`); `resample.fold` sums the first four and takes first/last ids.
- `channel_main.run_series` reads all bars of a series and calls `record_replay`; the same read feeds a flow step.
- The bar reader returns bars ordered and de-duplicated (a corrected bar replaces); the function sorts again so it
  does not depend on that.
- `FlowTracker` (`features/flow.py`) is the per-trade arithmetic and stays as the reference for a later notional
  version; this plan does not touch it.
- `test_pane_features.py` ties every `PANES` entry to the registry; `panes.test.ts` asserts the nine-entry order
  including `cvd`. Changing the pane to `cvd_base` edits that expected list (one line, listed in the outcome note).

## Decisions, and what each rejected

**D1. Derive from the stored bars, not from trades.** Rejected: a trade-level producer in the ingest (new coupling
to the socket process, a second 15m source beside the bars, and it recomputes what the bar builder already did).

**D2. Base units, named `*_base`, with an ADR.** The bar stores the aggressor split in base units; PRD §15.4 says
notional. Rejected: adding the quote split to the bar now (a schema change to the central table, forward-only, no
history); computing notional as base times VWAP (invents a number); naming the base-unit CVD `cvd` (it would claim
the PRD's quantity).

**D3. Runs, with breaks read from the bars**: a gap in `open_time_ns`; for sequential-id venues a trade-id jump
between bars and an id span that differs from `trade_count` within a bar. Rejected: wall-clock silence; trusting
the bars as continuous.

**D4. The worker writes the rows**, in the pass that already reads the bars. Rejected: a new process; the API
computing on read (the stored series would differ from the served one, and the features table is the PRD's source).

**D5. A bar with an id-span/count mismatch emits no row** and breaks the run on both sides: its delta is wrong and
a wrong sum is worse than a missing point. Rejected: emitting it with a flag nobody reads.

**D6. The chart breaks the line at a `cvd_run` change**, served as a feature. Rejected: a new API field; joining.

**D7. The pane entry becomes `cvd_base`, label "CVD (base)".** Rejected: keeping `cvd` and writing base-unit
values under it (a registered feature whose unit would lie).

## Tests (written first)

pytest, `@pytest.mark.trace("REQ-WP-088")`: `flow_rows` over fixtures (SC-001 numbers; zero-volume bar; first-bar
acceleration absent; forming bar excluded; shuffled input gives the same rows); no look-ahead (appending later bars
leaves earlier rows identical); breaks (a removed bar gives two runs, a trade-id jump, a count mismatch, a
non-sequential venue breaks only on a missing bar); the sink (written once, a second pass writes nothing; a pass
over a shorter series writes nothing); the worker wiring (a fake catalog: bars in, flow rows out, channels
unchanged); the registry (six `FeatureSpec`s; none named `cvd` or `delta_notional`). vitest: the CVD (base) pane is
live with rows; the line breaks at a `cvd_run` change; "no data" with none. Mutation specs for `flow_rows`.
SC-005 was measured on the live bars while specifying (Binance qualifies, Bybit and OKX do not), so the id checks are a venue-registry flag, `sequential_trade_ids`, true for Binance only.

## Constitution Check

I: a row at `t` uses only bars at or before `t`; forming bars excluded. III: rows appended after the latest on
record, never rewritten. VI: six `FeatureSpec`s. VII: one pure function for every pass and replay. X: nothing new
is a threshold. XIV: traced. **No violations**; the unit deviation is recorded ([[ADR-068]]).

## Risks

- The id-span check marks 6 of 18,597 live Binance 1m bars incomplete: real gaps, measured, not a counting artefact.
- Bybit and OKX breaks from missed trades inside a bar are invisible: stated.

## Project Structure

```text
src/channelflow/features/flow_bars.py     flow_rows(bars) and the run logic (new)
src/channelflow/features/flow.py          FeatureSpecs for the six *_base names
src/channelflow/connectors/venue.py       sequential_trade_ids flag on the venue registry (Binance only)
src/channelflow/tables/features.py        a sink that reads the latest row before it writes
src/channelflow/pipeline/channel_main.py  the flow step after the channel step
apps/web/src/panes.ts, FlowPane.tsx       cvd_base in PANES; break the line at a cvd_run change
vault/20-decisions/ADR-068.md             base units now, notional later
```
