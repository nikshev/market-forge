# Quickstart: Gap Policy Validation

## Prerequisites

- Running stack with bars for ETHUSDT 1h (148-bar hole)
- Config: `CHANNELFLOW_GAP_THRESHOLD=1` (default)

## Validation Scenarios

### 1. Unit tests: detector gap behavior
```bash
.venv/bin/python -m pytest tests/extrema/test_detector_gap.py -v
```
Fixtures:
- Contiguous bars: detector tracks normally
- 1 missing bar (threshold=1): treated as contiguous
- 2+ missing bars: detector resets state; no straddling confirmation
- Threshold=0: any gap triggers reset
- No look-ahead: appending later bars doesn't change earlier records

### 2. Unit tests: channel gap behavior
```bash
.venv/bin/python -m pytest tests/channels/test_channel_gap.py -v
```
Fixtures:
- Hole in series: channel window starts after hole; `window_short` until `lookback` contiguous bars
- Snapshot absent until bars after hole exist
- No look-ahead: earlier snapshot unchanged when later bars appended

### 3. Live validation: ETHUSDT 1h (148-bar hole)
```bash
.venv/bin/python -m pytest tests/extrema/test_live_gap_policy.py -v
```
- Detector records before/after hole are separate runs; zero straddling
- Channel snapshots before/after hole separate; `window_short` after hole until 60 bars
- Count of straddling records = 0

### 4. Confirmation lag
- Confirmed extremum has `confirmation_lag_ns` = confirming_bar.close - turn_bar.close
- `confirmation_lag_ns` > 0 and matches time difference