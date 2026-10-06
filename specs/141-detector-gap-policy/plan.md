# Implementation Plan: Extremum detector and channel gap policy

**Branch**: `141-detector-gap-policy` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/141-detector-gap-policy/spec.md`

## Summary

Policy 2 (restart at gap): on a hole (> `gap_threshold` missing bars, default 1), the extremum detector resets its state and the channel fits only to bars after the hole. No confirmation straddles a hole; channel snapshot absent until `lookback` contiguous bars exist. `gap_threshold` config (default 1). Confirmation lag adds `confirmation_lag_ns`. Policy 2 assumed per requirement recommendation; owner confirmation needed.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: 
- `extrema/detector.py` — directional-change detector (bar-counting, `confirmation_lag_bars`)
- `channels/window.py` — channel fit over `lookback` bars (default 60)
- `extrema/records.py` — extremum records with `confirmation_lag_bars`
- `channels/records.py` — channel snapshots

**Storage**: PostgreSQL (extrema, channel snapshots)

**Testing**: pytest, traceability markers

**Target Platform**: Linux containers

**Project Type**: Data pipeline (Python)

**Performance Goals**: Gap detection O(1) per bar; no look-ahead; live=replay

**Constraints**: 
- Principle I: no look-ahead — test appends later bars, checks earlier record unchanged
- Principle III: history immutable — snapshots never rewritten
- Principle X: `gap_threshold` configurable (default 1)
- Principle VII: live=replay — same code
- FR-016: failed loads stated, never blank
- Policy 2 assumed; owner confirmation needed

**Scale/Scope**: ETHUSDT 1h (148-bar hole), BTCUSDT 1h (109-bar hole), SOLUSDT 1h (154-bar hole); all timeframes

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. No look-ahead | Pass | Gap detection from bars ≤ instant; test appends later bars |
| II. Time is not one thing | Pass | Bar timestamps distinct; gap detection uses bar slots |
| III. History immutable | Pass | Snapshots never rewritten; new records for corrections |
| IV. Baselines before models | N/A | Deterministic models |
| V. Calibration, not accuracy | N/A | Not probabilistic |
| VI. Every feature documented | Pass | `gap_threshold` config, `confirmation_lag_ns` field |
| VII. Live and replay same code | Pass | Same detector/channel code |
| VIII. Connectors share one interface | N/A | No new connector |
| IX. No automatic execution | N/A | Analytics only |
| X. Thresholds are configuration | Pass | `gap_threshold` config (default 1) |
| XI. Results reproducible | Pass | Dataset version, config hash, commit hash |
| XII. Correctness precedes performance | Pass | Gap detection O(1) |
| XIII. Work incremental | Pass | Policy 2 only; fill/bridge out |
| XIV. Everything traceable | Pass | Spec has `traces: [REQ-WP-087]` |

No violations.

## Project Structure

```text
src/channelflow/
├── extrema/
│   ├── detector.py          # MODIFY: gap detection + state reset
│   ├── records.py           # MODIFY: add confirmation_lag_ns
│   └── __tests__/
│       └── test_detector_gap.py
├── channels/
│   ├── window.py            # MODIFY: gap-aware window selection
│   ├── records.py           # MODIFY: add window_short flag
│   └── __tests__/
│       └── test_channel_gap.py
├── config.py                # ADD: gap_threshold config
└── __tests__/
    └── test_live_gap_policy.py  # ETHUSDT 1h validation
```

## Phase 0: Research

No NEEDS CLARIFICATION. Research records decisions:

- **Gap detection**: from bars themselves — `next.open - prev.close > timeframe_ns * (gap_threshold + 1)` for "hole > threshold". Called at each bar step in detector and channel.
- **Detector reset**: on hole, set `direction=UNKNOWN`, `running_extreme=current_bar`, `open_candidate=None`. No confirmation emitted if turn before hole and confirm after.
- **Channel window**: after hole, window starts at first bar after hole; `window_bars` = min(`lookback`, contiguous bars after hole). Snapshot has `window_short` flag if `window_bars < lookback`.
- **Confirmation lag**: extremum record adds `confirmation_lag_ns` = `confirming_bar.close - turn_bar.close` (time). No straddling confirmation (turn before hole, confirm after) — detector state reset prevents it.
- **Config**: `CHANNELFLOW_GAP_THRESHOLD` (default 1) in `.env.example`; read in `config.py`.

## Phase 1: Design & Contracts

### data-model.md

```markdown
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
```

### quickstart.md

```markdown
# Quickstart: Gap Policy Validation

## Prerequisites
- Running stack with bars for ETHUSDT 1h (148-bar hole)

## Validation
1. Unit: `python -m pytest tests/extrema/test_detector_gap.py tests/channels/test_channel_gap.py -v`
   - Fixture with hole: detector resets, no straddling confirmation; channel fits post-gap only
   - Threshold config: 1 missing bar = contiguous, 2+ = hole; threshold=0 = any gap
2. Live: `python -m pytest tests/extrema/test_live_gap_policy.py -v`
   - ETHUSDT 1h (148-bar hole): detector/channel records before/after hole separate; zero straddling
3. Confirmation lag: confirmed extremum has `confirmation_lag_ns` > 0
```