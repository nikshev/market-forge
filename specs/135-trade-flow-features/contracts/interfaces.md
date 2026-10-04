# Contracts: flow features from bars

- `flow_rows(bars: Sequence[Bar], *, sequential_ids: bool) -> list[FlowRow]`: final bars of one series in any order;
  returns rows in time order; pure, no I/O, no clock.
- `flow_feature_rows(rows, venue, symbol, timeframe_ns) -> list[row]`: the long form, via `feature_rows`.
- Worker: after `record_replay` for a series, `flow_rows` over the same bars, written after the latest `cvd_base`
  row on record for `(venue, symbol, timeframe)`.
- HTTP: unchanged; `/api/v1/features/timeseries` returns the six names inside `values`.
- UI: the pane `cvd_base` (label "CVD (base)") breaks its line where consecutive points carry different `cvd_run`.
