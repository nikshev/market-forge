# API Contracts: Cross-venue Consensus

## GET /api/v1/consensus

Returns per-bar consensus mids for a window.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `venue` | string | yes | Exchange venue (e.g., `binance`) |
| `symbol` | string | yes | Trading symbol (e.g., `BTCUSDT`) |
| `timeframe_ns` | number | yes | Bar width in nanoseconds |
| `window` | string | yes | One of `4h`, `24h`, `7d` |
| `at_ns` | string (bigint) | no | Instant for AS-SEEN-THEN; omitted for latest |

### Response

```json
{
  "consensus": [
    {
      "bar_close_ns": "1789344000000000000",
      "consensus_mid": "65432.10",
      "venue_count": 2,
      "refusal_reason": null
    },
    {
      "bar_close_ns": "1789344900000000000",
      "consensus_mid": "65435.20",
      "venue_count": 1,
      "refusal_reason": "one_venue"
    }
  ],
  "window": "24h",
  "at_ns": "1789344900000000000"
}
```

### Refusal Reasons

- `stale` — quote older than `staleness_ns`
- `future` — quote timestamp > `at_ns`
- `one_venue` — only one venue had fresh quote
- `no_quotes` — no quotes for any venue at that bar

---

## GET /api/v1/features/timeseries

Returns `venue_basis_bps` for the viewed venue.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `venue` | string | yes | Exchange venue |
| `symbol` | string | yes | Trading symbol |
| `timeframe_ns` | number | yes | Bar width in nanoseconds |
| `feature` | string | yes | Must be `venue_basis_bps` |
| `start_ns` | string (bigint) | yes | Window start |
| `end_ns` | string (bigint) | yes | Window end |

### Response

```json
{
  "points": [
    {
      "bar_close_ns": "1789344000000000000",
      "venue_basis_bps": "12.5"
    },
    {
      "bar_close_ns": "1789344900000000000",
      "venue_basis_bps": "-8.3"
    }
  ]
}
```

### FeatureSpec Registration

```python
FeatureSpec(
    name="venue_basis_bps",
    unit="bps",
    cadence="bar_close",
    source="cross-venue consensus",
    description="Viewed venue's basis to cross-venue consensus mid"
)
```