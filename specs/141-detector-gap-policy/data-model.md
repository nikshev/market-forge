# Data Model: Detector/Channel Gap Policy

## Entities

### Gap
- `after_close_ns: int` — close of bar before hole
- `before_open_ns: int` — open of bar after hole
- `missing_bars: int` — number of missing bar slots

### DetectorState (internal)
- `direction: Direction` — UP/DOWN/UNKNOWN
- `running_extreme: Decimal` — price of running extreme
- `open_candidate: Candidate | None` — unconfirmed turn
- `last_bar_close_ns: int` — last processed bar close

### ChannelSnapshot (extended)
- `window_bars: int` — actual bars used (<= lookback)
- `window_short: bool` — true if window_bars < lookback
- `first_bar_after_gap_ns: int | null` — first bar in window after gap

### ExtremumRecord (extended)
- `confirmation_lag_bars: int` — existing
- `confirmation_lag_ns: int` — NEW: time difference confirming_bar.close - turn_bar.close

## State Transitions

Detector:
- Normal bar: update direction/running_extreme/candidate
- Hole detected: reset direction=UNKNOWN, running_extreme=current_bar, candidate=None
- First bar after hole: fresh observation

Channel:
- Normal bar: window = last `lookback` bars
- Hole detected: window starts at first bar after hole
- `window_bars = min(lookback, contiguous_bars_after_hole)`
- `window_short = window_bars < lookback`