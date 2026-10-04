---
id: OUT-2026-10-04-implement-trade-flow-features
step: implement
records: [REQ-WP-088]
commit: 9c04931
---

## What was done

CVD and the §15.4 trade-imbalance features are produced from the aggressor volumes the bars already store, and the
CVD pane draws them. **Live on the running stack:** the worker's first pass after deployment wrote flow rows for 84,971
bars across every series and timeframe, and `/api/v1/features/timeseries` for `binance` `BTCUSDT` at 15m returns
`cvd_base`, `delta_base`, `normalized_delta_base`, `cvd_base_slope`, `cvd_base_acceleration` and `cvd_run`.

- `features/flow_bars.py`: pure `flow_rows(bars, sequential_ids=...)`, six registered features, run logic.
- `tables/features.py`: `latest_flow_times` (one arrow read per pass) and `write_flow` (append-only after the latest
  row on record; a second pass writes nothing).
- `pipeline/channel_main.py`: `write_flow_features(catalog, all_bars)` in `run_pass`, on the bars the pass already
  reads; one series failing is reported and stops nothing, including the channel step.
- `connectors/venue.py`: `sequential_trade_ids` on the venue registry, true for Binance only.
- Web: the pane entry is `cvd_base` ("CVD (base)"); `segments()` splits a series where `cvd_run` changes and
  `FlowPane` draws one polyline per run on a common scale.
- [[ADR-068]]: base units, not notional, knowingly, with the way back.

**RED first.** Four Python files and one vitest file written against unchanged source:

    ModuleNotFoundError: No module named 'channelflow.features.flow_bars'   (all four Python files)
    Failed Tests 5   (cvdBasePane.test.tsx: no `cvd_base` pane, no `segments`)

**After.** Python unit suite 3056 passed; web 411/411 (406 + 5); `make lint`, `make typecheck`, `make web-typecheck`
clean; `make web-build` green. Mutation sweep `tests/mutations/flow_bars.toml`: 13 mutants, 13 caught, after one
survived the first time (below). **Bundle gzip** 164,230 B -> 164,428 B (+198 B).

## Edits to existing tests (all one-liners, each a consequence of the rename or the new features)

- `test_truncation_parity.py` (REQ-NRT-LEAK, hard-gated): six new truncation cases for the six features
  (`_flow_bar_cases`: the row at `t` from bars through `t` equals the row at `t` from all the bars, with a missing
  bar before `t` and different bars after it), and the counts 55 -> 61 features, 39 -> 45 cases, 16 refusals unchanged.
  The gate failed by name the moment the features were registered, which is what it is for.
- `test_pane_features.py`: the order-flow pane is `cvd_base`.
- `panes.test.ts`: the expected pane list has `cvd_base` first of the features.
- `FlowPane.test.tsx`: one case names the CVD (base) button. Others use `cvd` only as a free feature name for
  `paneSeries`, which accepts any, and are untouched.
- REQ-WP-084's and REQ-WP-085's own new tests that named the "CVD" button now name "CVD (base)".

## What the mutation sweep found

One mutant survived: removing the reset of the previous slope at a break, so the first bar of a **new** run would
inherit an acceleration from the old one. My tests checked "no acceleration" only for the first bar of the whole series.
Added `test_the_first_bar_of_a_new_run_has_no_acceleration_either`; 13 of 13 now caught.

## What looking at the live screenshots showed

`docs/ui/cvd-pane-{light,dark}.png`, **live data, no stub**:

1. The pane draws a real CVD, **in separate pieces**: five runs in these 193 15m bars (`cvd_run` 10..14), broken where
   the bars have gaps, each run starting from zero. The empty stretch in the middle of the pane is a real hole in the
   BTCUSDT 15m bars (the same hole the volume pane showed).
2. It is **not** a continuous line, and it should not be: joining across a missing bar would say the sum is
   comparable across it. A reader comparing the level of one piece with another is told by the break not to.
3. The candles above sit on an index axis and hide the hole; the pane's time axis shows it. [[REQ-WP-086]] is about that.
4. The pane is 720 px wide on a 1,150 px chart (unchanged from the other panes).

## What was measured before it was relied on

Binance 1m bars, 2026-10-04: BTCUSDT 18,591 of 18,597 have id span == trade count; 18,586 of 18,587 consecutive pairs
are contiguous (ETHUSDT 15,665 of 15,672; 15,663 of 15,664). Bybit ids are not numeric; OKX ids are numeric but not
sequential (2,682 of 2,734 bars disagree). So the id checks are a registry flag, true for Binance only. They found real
breaks: 6 incomplete bars of 18,597.

## What is still open

- **Notional.** This is base units (coins), not the PRD's notional (dollars); [[ADR-068]] has the way back (store the
  quote split in the bar). Bybit and OKX cannot detect a missed trade inside a bar, only a missing bar.
- **Every other pane still reads "no data":** OFI and depth imbalance need a book subscription; OI, funding, basis,
  liquidations need derivatives feeds; the DEX panes need DEX ingest.
- The first worker pass wrote 84,971 bars of history in one go; later passes write only new bars.
