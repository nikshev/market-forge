# Data model: the lower pane chart

No stored data and no API change.

| Name | Type | Notes |
|---|---|---|
| `ChartHandle` | `{ api: IChartApi; candles: () => ISeriesApi<"Candlestick"> \| null }` | given by `Chart` through `onReady`, `null` after unmount |
| `AlignedPoint` | `{ time: number } \| { time: number; value: number }` | one per bar time; no `value` = whitespace |
| `alignToBars(bars, points)` | `AlignedPoint[]` | at each bar's `close_time_ns` seconds; a point goes to the bar whose `(open, close]` contains its instant, the later wins |
| `runsOf(points, features)` | `AlignedPoint[][]` | one array of real values per `cvd_run`; whitespace-free |
| volume colour | `"up"` if `close >= open` else `"down"` | the candle's own colours |
