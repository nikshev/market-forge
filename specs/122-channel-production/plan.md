# Implementation Plan: Channels, signals and extrema produced for the running deployment

**Branch**: `122-channel-production` | **Date**: 2026-09-24 | **Spec**: `specs/122-channel-production/spec.md`

**Input**: Feature specification from `/specs/122-channel-production/spec.md`

## Summary

REQ-WP-077 wires the existing `record_replay` function (already correct and tested in `channelflow.pipeline.replay`) into a periodic pass that reads the bars the deployment already has, at every configured timeframe, and writes channel snapshots, signals, confirmed extrema, and extremum candidates. The missing piece is not an algorithm but a process - the "deployment work" [[REQ-PIPE-001]] deliberately excluded when it chose replay over daemon.

**Technical approach**: a new `channelflow.pipeline.channel_main` module that mirrors `resample_main.py`'s loop shape: `--once` (default) or `--loop <interval>` to repeat every interval, one `(venue, symbol, timeframe)` series per pass, per-series failure isolation, and idempotence verified by watermark-driven row counts rather than inherited trust.

## Technical Context

**Language/Version**: Python 3.12 (project runtime)

**Primary Dependencies**: FastAPI, PostgreSQL, MinIO/S3, Iceberg tables (no new dependencies)

**Storage**: PostgreSQL for catalog metadata; MinIO for warehouse; Iceberg tables for bars, channels, signals, extrema

**Testing**: pytest (unit + integration), mutation sweep via `tests/mutations/`

**Target Platform**: Linux server / Docker Compose deployment stack

**Project Type**: Python web-service with data pipeline services

**Performance Goals**: Channel pass every 5 minutes by default; one pass over all configured timeframes completes in bounded time regardless of failures

**Constraints**:
- No look-ahead (Principle I): a pass at time `t` uses only data with `event_time <= t`
- Append-only, immutable tables (Constitution III, PRD §29.6): snapshots never rewritten
- One timeframe failing MUST NOT stop the pass (PRD §6.2, §25.1)
- Idempotent re-runs: zero new rows on unchanged bars (SC-003)
- Signal final-state-only: exactly one row per signal, never one per bar

**Scale/Scope**: Deployment with 3 configured timeframes (1m, 5m, 1h example) and up to 3 symbols (BTCUSDT, ETHUSDT, SOLUSDT); the pass discovers series from the `bars` table rather than duplicating configuration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **No look-ahead** - PASS. The pass reads the `bars` table as it exists at pass time; `record_replay` consumes only bars with `event_time <= t` that were available at the decision moment. No future data is used.
2. **Correctness, replay parity, data integrity over performance** - PASS. The pass reuses the tested `record_replay` function; no optimization that could break parity is introduced.
3. **Immutable append-only** - PASS. The pass writes through the same recorders as `record_replay` (watermark-checked), never rewrites snapshots.
4. **One process per series** - PASS. The pass discovers series from the `bars` table; each series is processed independently, so one symbol's failure cannot stall another.
5. **Environment is the only input** - PASS. Configuration comes only from `CHANNELFLOW_TIMEFRAMES` and `CHANNELFLOW_CHANNEL_INTERVAL`; no defaults that could hide a misconfiguration.

## Project Structure

### Documentation (this feature)

```text
specs/122-channel-production/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (created by /sdd-tasks)
```

### Source Code (repository root)

```text
src/channelflow/pipeline/
├── channel_main.py      # New: periodic pass loop (FR-001)
├── ingest_main.py       # Existing: ingest daemon
├── resample_main.py     # Existing: resampler loop (pattern for channel_main)
└── replay.py            # Existing: record_replay (already correct)

docker-compose.yml
├── worker               # New service: runs channel_main --loop
└── resample             # Existing service: runs resample_main --loop

.env.example
└── CHANNELFLOW_CHANNEL_INTERVAL=5m
```

**Structure Decision**: Follow the established `resample_main.py` pattern exactly - one module owns the loop and catalog, pure `run_series`/`run_pass` functions are testable, and the compose file adds a `worker` service using the same image as the API. No new abstractions beyond what `resample_main.py` already established.

## Complexity Tracking

> Not needed. The design reuses existing, tested components (`record_replay`, `bars_table.read_bars`, `parse_list`) and follows the already-validated `resample_main.py` pattern. No constitution violations.
