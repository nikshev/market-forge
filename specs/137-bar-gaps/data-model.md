# Data model: gaps

No stored data and no API change.

| Name | Type | Notes |
|---|---|---|
| `Gap` | `{ afterCloseNs: bigint; beforeOpenNs: bigint; missing: number }` | between two consecutive bars; `missing = round((beforeOpenNs - afterCloseNs) / window)` |
| gap marker | `SeriesMarker` | at the first bar after the gap: amber square, `text` `"N missing"`, id `gap-<time>` |
| notice line | string | `"148 bars missing, 26.09 06:00 to 02.10 11:00"` (UTC) |
