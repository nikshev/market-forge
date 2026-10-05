# API Contracts: Live Refresh (Stage 1)

No new endpoints. The refresh re-uses the exact same endpoints the initial load calls, with identical query parameters.

## Endpoints

### GET /api/v1/bars
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `venue` | string | yes | Exchange venue (e.g., `binance`) |
| `symbol` | string | yes | Trading symbol (e.g., `BTCUSDT`) |
| `timeframe_ns` | number | yes | Bar width in nanoseconds |
| `limit` | number | no | Max bars to return (default 500) |

Response: `{ bars: BarOut[] }` — `BarOut` carries `open_time_ns`, `close_time_ns`, `open`, `high`, `low`, `close`, `volume_base`, `is_final`.

### GET /api/v1/channels
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `venue` | string | yes | Exchange venue |
| `symbol` | string | yes | Trading symbol |
| `timeframe_ns` | number | yes | Bar width in nanoseconds |
| `at_ns` | string (bigint) | yes | Instant for AS-SEEN-THEN snapshot |
| `as_seen_then` | string (bool) | yes | `true` for AS-SEEN-THEN, `false` for CURRENT REFIT |

Response: `ChannelOut` — centre, boundaries, lookback, or 404 if no snapshot.

### GET /api/v1/features/timeseries
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `venue` | string | yes | Exchange venue |
| `symbol` | string | yes | Trading symbol |
| `timeframe_ns` | number | yes | Bar width in nanoseconds |
| `start_ns` | string (bigint) | yes | Window start |
| `end_ns` | string (bigint) | yes | Window end |

Response: `FeatureSeriesResponse` — `{ points: FeaturePointOut[] }`.

### GET /api/v1/extrema
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `instrument_id` | string | yes | `venue:symbol` |
| `timeframe_ns` | number | yes | Bar width in nanoseconds |
| `as_of_ns` | string (bigint) | no | Instant for AS-SEEN-THEN; omitted for CURRENT REFIT |

Response: `ExtremaResponse` — `{ confirmed: ExtremumOut[], candidates: ExtremumOut[] }`.

### GET /api/v1/volume-profile (when `volume_profile` layer on)
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `venue` | string | yes | Exchange venue |
| `symbol` | string | yes | Trading symbol |
| `window` | string | yes | One of `4h`, `24h`, `7d` |
| `at_ns` | string (bigint) | no | Instant; omitted for latest closed block |

Response: `VolumeProfileOut` — bins, POC, value area, coverage; 404 if no bins collected.

### GET /api/v1/dex/depth (when link names a pool)
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chain_id` | number | yes | EVM chain ID |
| `pool` | string | yes | Pool address |
| `at_ns` | string (bigint) | yes | Instant |

Response: `DexDepthResponse` — liquidity bands at the instant.

## Notes

- All `_ns` parameters are stringified `bigint` on the wire (instants); durations stay `number`.
- The API enforces no look-ahead (Principle I): `at_ns` / `as_of_ns` bounds the data to what was available at that instant.
- The worker's 5-minute passes (`CHANNELFLOW_RESAMPLE_INTERVAL`, `CHANNELFLOW_CHANNEL_INTERVAL`) set the freshness floor; the page cannot show a bar the API does not yet serve.