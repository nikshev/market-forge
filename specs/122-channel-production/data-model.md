# Phase 1: Design — Data Model & Interface

**Feature**: `specs/122-channel-production/spec.md` | **Requirement**: [[REQ-WP-077]]

## Data Model

### New code artifacts (for this feature only)

- **`channelflow.pipeline.channel_main`**: New module — periodic pass that runs `record_replay` on every configured timeframe. No new database tables; writes to existing tables via `record_replay`.

### Existing tables involved

All tables referenced in the feature already exist as part of [[REQ-WP-001]] (the plane). This feature writes to:

- `channel_snapshots` — populated by `ChannelRecorder` via `record_replay`
- `signals` (two tables: core + transitions) — populated by `SignalRecorder` via `record_replay`
- `confirmed_extrema` — populated by `ExtremumRecorder` via `record_replay`
- `extremum_candidates` — populated by `ExtremumRecorder` via `record_replay`

Each table is append-only and immutable ([[REQ-STORE-001]]).

### Key types from the plane

The existing recorders (`ChannelRecorder`, `SignalRecorder`, `ExtremumRecorder`) already embody the invariants:

- **ChannelRecorder**: writes one row per signal per `(venue, symbol, timeframe, as_of_ns)`
- **SignalRecorder**: writes exactly one row per signal per `(venue, symbol, timeframe, opened_at_ns)`, with final state only
- **ExtremumRecorder**: writes to both `confirmed_extrema` and `extremum_candidates` tables

These invariants are inherited by the new feature because it calls `record_replay` unchanged.

## Interface Contracts

### New CLI contract (`channel_main.py`)

The new module's public interface matches the proven pattern from `resample_main.py`:

```bash
# Run a single pass and exit
python -m channelflow.pipeline.channel_main

# Run periodically, every interval
python -m channelflow.pipeline.channel_main --loop <interval>
```

**Arguments**:

- `--once`: Run one pass and exit (default)
- `--loop <interval>`: Repeat every interval (e.g., `5m`, `1h`, `2d`, `3600` for seconds)
- `interval` grammar: `<number>[s|m|h|d]` from `resample_main.py`

**No environment variables require?** Only `CHANNELFLOW_TIMEFRAMES` and `CHANNELFLOW_CHANNEL_INTERVAL` (new).

### No new database API

This feature does **not** expose a new API endpoint. The contract is the periodic pass that produces data; any downstream consumer reads from the existing tables ([[REQ-WP-028]], `GET /api/v1/channels`).

### No new configuration beyond existing

- `CHANNELFLOW_TIMEFRAMES`: The list of target timeframes (already used by `resample_main.py`)
- `CHANNELFLOW_CHANNEL_INTERVAL`: New — how often to run the channel pass (default `5m`, matching `resample_main.py`)

No new tables, no new indices, no new schema migrations.

## Quickstart Guide

### Prerequisites

- The development stack running with `make up` (`postgres`, `minio`, `redpanda`, `api`, `ingest-*`, `resample`, `maintenance`)
- Bars data already present in the `bars` table for the configured timeframes

### How to start the channel production

```bash
# Run a single pass (equivalent to a manual replay)
CHANNELFLOW_TIMEFRAMES=5m,15m,30m,1h,4h,1d,1w \
CHANNELFLOW_CHANNEL_INTERVAL=5m \
python -m channelflow.pipeline.channel_main --once

# Run continuously, every 5 minutes (as a service)
CHANNELFLOW_TIMEFRAMES=5m,15m,30m,1h,4h,1d,1w \
CHANNELFLOW_CHANNEL_INTERVAL=5m \
python -m channelflow.pipeline.channel_main --loop 5m
```

### What to observe

- Print statements match the `resample_main.py` pattern:
  ```
  (venue) (symbol) (timeframe): channel snapshots: N, signals: M, confirmed extrema: K, extremum candidates: L
  ```

- Failures per series printed with the same format as resample:
  ```
    BTCUSDT 1h: FAILED — ValueError: Something went wrong
  ```

### How to verify it works

1. **Check API endpoint**: After a pass, `GET /api/v1/channels` returns data for a `(venue, symbol, timeframe)` that has bars.

2. **Verify idempotence**: Run the pass twice, count rows before/after second pass. The second pass should write zero new rows.

3. **Check partial failure**: Cause one timeframe to fail (e.g., malformed bars), observe logs and verify remaining timeframes complete.

4. **Check timeframe coverage**: Configure three timeframes (`1m,5m,1h`), verify all three appear in the channel snapshots.

5. **Check logs**: One line per successful `(venue, symbol, timeframe)` series.

### Docker-Compose deployment

Add the `worker` service to `docker-compose.yml`:

```yaml
worker:
  build:
    context: .
    dockerfile: Dockerfile
  command:
    - python
    - -m
    - channelflow.pipeline.channel_main
    - --loop
    - ${CHANNELFLOW_CHANNEL_INTERVAL}
  environment:
    CHANNELFLOW_CATALOG_URI: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    CHANNELFLOW_WAREHOUSE: s3://${MINIO_BUCKET}/warehouse
    CHANNELFLOW_S3_ENDPOINT: http://minio:9000
    CHANNELFLOW_S3_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
    CHANNELFLOW_S3_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
    CHANNELFLOW_S3_REGION: us-east-1
    CHANNELFLOW_TIMEFRAMES: ${CHANNELFLOW_TIMEFRAMES}
    CHANNELFLOW_CHANNEL_INTERVAL: ${CHANNELFLOW_CHANNEL_INTERVAL}
  depends_on:
    postgres:
      condition: service_healthy
    minio:
      condition: service_healthy
    api:
      condition: service_healthy
  restart: unless-stopped
```

Add the environment variable to `.env.example`:

```env
CHANNELFLOW_CHANNEL_INTERVAL=5m
```

The service uses the same image and storage configuration as the other pipeline services (`api`, `ingest-binance`, `resample`, `maintenance`).

## Notes

The contract is minimal by design: the feature is entirely about wiring `record_replay` into a loop. No new tables, no new APIs, no new configuration beyond an interval.

This matches the spec's assumption that `record_replay` is already correct and tested; this feature only wires it into a scheduled loop.

The `contracts/` directory is intentionally empty for this feature: there is no new API or client interface to document. If this changed (e.g., a new REST endpoint), we would add contracts for it here.
