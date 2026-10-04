# Data model: the volume pane

No stored data and no API change.

| Name | Type | Notes |
|---|---|---|
| `BAR_PANES` | `Pane[]` | `[{ feature: "volume", label: "Volume" }]`; not a registered feature. |
| `ROW` | `Pane[]` | `[...BAR_PANES, ...PANES]`: what the pane row renders and selection walks. |
| `volumeSeries(bars)` | `PaneSeries` | `points = final bars → { at_ns: open_time_ns, value: Number(volume_base) }`, non-finite skipped, sorted by time; `state` `ok` or `empty`. |
| `barsLoaded` | boolean (`App` state) | True once `fetchBars` answered ok, including with no bars. Tells "no bars yet" from "the bars are none". |
| `availablePanes(points, bars)` | `ReadonlySet<string>` | the feature panes with data (as before) plus `"volume"` when `volumeSeries(bars).state === "ok"`. |
