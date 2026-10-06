# Research: Detector/Channel Gap Policy

## R1. Gap detection from bars themselves

The detector and channel must detect gaps from the bars they are given, not from a caller (per §13.1: model guards its own invariant). A hole is detected when `next_bar.open_time_ns - prev_bar.close_time_ns > timeframe_ns * (gap_threshold + 1)`.

- `gap_threshold = 1` (default): 1 missing bar = contiguous (bridge); 2+ missing = hole (restart).
- `gap_threshold = 0`: any gap restarts.
- Checked at each bar step in both detector and channel.

## R2. Detector state reset on hole

The directional-change detector tracks `direction`, `running_extreme`, `open_candidate` across bars. On a hole:
- These are reset: `direction=UNKNOWN`, `running_extreme=first_bar_after_hole`, `open_candidate=None`.
- No confirmation emitted if turn before hole and confirming bar after hole.
- Confirmation lag in bars only counted from bars after hole (contiguous series).

## R3. Channel fits only to bars after hole

The channel's `lookback` window (default 60) must not include bars from before the hole.
- Window starts at first bar after hole.
- `window_bars = min(lookback, contiguous_bars_after_hole)`.
- Snapshot carries `window_short=true` if `window_bars < lookback`.
- Snapshot absent if `window_bars == 0` (no bars after hole yet).

## R4. Confirmation lag in time (not just bars)

§32: "missing bars is a health metric; a lag in bars is only meaningful on a contiguous series."
- Extremum record adds `confirmation_lag_ns = confirming_bar.close_time_ns - turn_bar.close_time_ns`.
- No straddling confirmation: detector reset prevents turn before hole + confirm after hole.
- Live ETHUSDT 1h (148-bar hole): records before/after hole are separate runs; zero straddling.

## R5. Configuration

`CHANNELFLOW_GAP_THRESHOLD` (default 1) in `.env.example`:
- 1: 1 missing bar = bridge, 2+ = hole (restart)
- 0: any gap restarts
- >1: hole size > threshold restarts

Principle X satisfied.

## R6. Live validation

ETHUSDT 1h has 148-bar hole (26.09 06:00 → 02.10 11:00). Validation:
- Detector: LOW at 25.09 22:00 confirmed at 02.10 12:00 with lag_bars=10 (today). With gap policy: that confirmation is NOT emitted (turn before hole, confirm after). New confirmation after hole with lag measured from bars after hole only.
- Channel: 02.10 fit window starts at first bar after hole; window_short until 60 contiguous bars.
- Count of straddling records = 0.