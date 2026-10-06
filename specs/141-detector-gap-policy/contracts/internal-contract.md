# Contracts: Detector/Channel Gap Policy

No new API endpoints. Changes are internal to detector and channel models.

## Modified Models

### ExtremumRecord (extended)

```python
class ExtremumRecord:
    # existing fields...
    type: Literal["HIGH", "LOW"]
    at_ns: int
    known_at_ns: int
    confirmation_lag_bars: int
    confirmation_lag_ns: int  # NEW: time difference confirming_bar.close - turn_bar.close
```

### ChannelSnapshot (extended)

```python
class ChannelSnapshot:
    # existing fields...
    centre: list[LinePoint]
    upper: list[LinePoint]
    lower: list[LinePoint]
    lookback: int
    window_bars: int          # NEW: actual bars used (<= lookback)
    window_short: bool        # NEW: true if window_bars < lookback
    first_bar_after_gap_ns: int | null  # NEW: first bar in window after gap
```

## Internal Interfaces

### Detector.run(bars: list[Bar]) -> list[ExtremumRecord]

- Detects gaps at each bar step: `gap = next.open - prev.close > timeframe * (gap_threshold + 1)`
- On gap: resets `direction`, `running_extreme`, `open_candidate`
- No confirmation emitted straddling a gap
- Confirmation lag in bars counted only from contiguous bars after gap
- Returns extremum records with `confirmation_lag_ns`

### Channel.fit(bars: list[Bar], lookback: int) -> ChannelSnapshot

- Detects gaps same way
- Window starts at first bar after gap
- `window_bars = min(lookback, contiguous_bars_after_gap)`
- `window_short = window_bars < lookback`
- Returns snapshot with `window_short` flag

## Configuration

```bash
CHANNELFLOW_GAP_THRESHOLD=1  # default 1; 0 = any gap restarts; >1 = hole size > threshold
```

## Configuration Access

```python
# src/channelflow/config.py
GAP_THRESHOLD = int(os.getenv("CHANNELFLOW_GAP_THRESHOLD", "1"))
```