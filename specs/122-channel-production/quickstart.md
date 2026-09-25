# Phase 1: Contracts & Quickstart

**Feature**: `specs/122-channel-production/spec.md` | **Requirement**: [[REQ-WP-077]]

## Contracts

This feature introduces no new external API contracts. It is an internal pipeline service.

The only new CLI contract is:

### `python -m channelflow.pipeline.channel_main`

| Argument | Description | Example |
|---|---|---|
| `--once` | Run one pass and exit (default) | `--once` |
| `--loop <interval>` | Repeat every interval | `--loop 5m` |

Interval grammar: `<number>[s|m|h|d]` — same grammar as `CHANNELFLOW_RESAMPLE_INTERVAL`.

**Environment variables**:

| Variable | Description | Required | Default |
|---|---|---|---|
| `CHANNELFLOW_TIMEFRAMES` | Comma-separated timeframes to produce | Yes | — |
| `CHANNELFLOW_CHANNEL_INTERVAL` | Loop interval | No | `5m` |

No new tables, indices, or schema migrations. Writes to existing immutable tables via `record_replay`.

## Quickstart

### Prerequisites

- Development stack running (`make up`)
- Bars data present in `bars` table for configured timeframes (produced by `resample` service)
- `CHANNELFLOW_TIMEFRAMES` set (e.g., `5m,15m,30m,1h,4h,1d,1w`)

### Run a single pass

```bash
CHANNELFLOW_TIMEFRAMES=1m,5m,1h \
CHANNELFLOW_CHANNEL_INTERVAL=5m \
python -m channelflow.pipeline.channel_main --once
```

### Run the loop

```bash
CHANNELFLOW_TIMEFRAMES=1m,5m,1h \
CHANNELFLOW_CHANNEL_INTERVAL=5m \
python -m channelflow.pipeline.channel_main --loop 5m
```

### Verify

1. **Channel appears**: After a pass, `GET /api/v1/channels` returns data for a `(venue, symbol, timeframe)` with bars
2. **Idempotence**: Run the pass twice — second pass writes zero new rows
3. **Partial failure**: Observe logs confirming one timeframe failing does not stop others
4. **Timeframe coverage**: All configured timeframes have rows in `channel_snapshots`

### In Docker Compose

Add the `worker` service to `docker-compose.yml` and `CHANNELFLOW_CHANNEL_INTERVAL=5m` to `.env.example`. The service uses the same image as `api` with a different command.
