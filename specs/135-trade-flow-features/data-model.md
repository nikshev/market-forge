# Data model: flow features from bars

No new table. Rows go to the features table in the long form (`at_ns` = the bar's `close_time_ns`, `venue`,
`symbol`, `timeframe_ns`, `feature_name`, `value`).

| feature name | definition (per final bar of a series) | notes |
|---|---|---|
| `delta_base` | `aggressive_buy_base − aggressive_sell_base` | base units |
| `cvd_base` | running sum of `delta_base` within the run | resets to the first bar's delta at a run start |
| `normalized_delta_base` | `delta_base / volume_base` | absent when `volume_base` is 0 |
| `cvd_base_slope` | `delta_base / bar seconds` | change of CVD per second over the bar |
| `cvd_base_acceleration` | `(slope − previous bar's slope) / bar seconds` | absent in a run's first bar |
| `cvd_run` | integer, 0 for the first run of the series, +1 at each break | the chart breaks the line when it changes |

Run breaks: `open_time_ns` gap greater than the timeframe; for sequential-id venues, `next.first_trade_id !=
prev.last_trade_id + 1`; a bar with `last − first + 1 != trade_count` produces no row and breaks on both sides.
