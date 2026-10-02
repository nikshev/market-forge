# Contract: what logs at which level, and the compose cap

## Levels

| event | level | frequency |
|---|---|---|
| a trade normalised, a bar window checked, a frame received, a step taken | DEBUG | per trade / frame / step |
| `FrameArchive.flush` that wrote an object | INFO | at most once a minute per process |
| `FrameArchive.flush` with nothing to write | DEBUG | |
| `S3ObjectStore.put` succeeded | DEBUG | |
| a connection opened, closed, reconnected | INFO | per event |
| a connection declared **down** | WARNING | once on entry; failures at attempts 1, 2, 4, 8… |
| a connection **recovered** | INFO | once, with attempts and time down |
| a venue's refusal (`rejection()`), a failed open, a reader ending | WARNING | per event |

**The rule**: nothing on the per-trade, per-frame or per-step path writes at INFO or
above. A persisting condition writes on entry and on exit.

## Configuration

| variable | default | meaning |
|---|---|---|
| `CHANNELFLOW_LOG_LEVEL` | `INFO` | root level, applied in `main()` |
| `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` | per policy (60) | silence tolerated before a reconnect |
| `CHANNELFLOW_LOG_MAX_SIZE` | `20m` | compose `max-size`, every service |
| `CHANNELFLOW_LOG_MAX_FILE` | `3` | compose `max-file`, every service |

Compose forwards only the variables a service names, so the first two are listed in every
ingest service's `environment` as `${…:-}`; an empty value means unset.

`logging.basicConfig` moves from module import into `main()`. Importing
`channelflow.pipeline.ingest_main` no longer reconfigures the root logger.

**Removed**: `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER`, its `IngestSettings` field and its
tests. It multiplied a quantity that meant something else on each venue.

## Compose

```yaml
x-logging: &default-logging
  driver: json-file
  options:
    max-size: ${CHANNELFLOW_LOG_MAX_SIZE:-20m}
    max-file: "${CHANNELFLOW_LOG_MAX_FILE:-3}"

services:
  <every service>:
    logging: *default-logging
```

`tests/unit/deploy/test_compose_logging.py` reads the file as YAML and fails for any
service — including `minio_init` and any added later — with no `logging.options.max-size`.

## Measured, before and after

Bytes per minute for each ingest service, 60-second windows. **Before**, 2026-10-02:

| service | bytes/min | lines/min |
|---|---|---|
| ingest-binance | 152,511 | 1,292 |
| ingest-binance-eth | 88,148 | 760 |
| ingest-binance-sol | 63,384 | 536 |
| ingest-bybit | 576,722 | 3,216 |
| ingest-okx | 57,152 | 300 |

**After** is recorded in the implement outcome note. The expectation, from the rule:
about one line a minute per process, so on the order of 100 bytes a minute, against a
ceiling of 10 MB a day (SC-004).
