# Data model: the volume profile

Table `volume_bins` (event-time column `close_time_ns`, the block's close):

| column | type | notes |
|---|---|---|
| `close_time_ns` | timestamp_ns | block open + block length |
| `venue`, `symbol` | string | |
| `block_open_time_ns`, `block_ns` | int64 | 5 minutes by default |
| `bin_width` | decimal | quote units; the grid is `floor(price / bin_width)` |
| `bin_index` | int64 | |
| `buy_base`, `sell_base`, `unknown_base` | decimal | by the trade's aggressor side only |
| `trades` | int64 | |

Response `VolumeProfileOut`: `bins[]` (`low`, `high`, `buy`, `sell`, `unknown`, `trades`), `poc_index`, `value_area` (`low`, `high`),
`as_of_ns`, `window_ns`, `covers_from_ns`, `covered_ns`, `complete`, `bin_width`, `left_out_rows`.
