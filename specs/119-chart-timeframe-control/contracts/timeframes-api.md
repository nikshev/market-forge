# Contract: `GET /api/v1/timeframes`

One new read. Read-only like every route in §28 (Principle IX), unauthenticated
like the rest of the prefix, and constant per process: the set is parsed once at
startup from configuration and never re-read.

## Request

```text
GET /api/v1/timeframes
```

No parameters. A client that sends any is ignored, as FastAPI ignores unknown
query parameters elsewhere in this API.

## Response

```json
{
  "timeframes": [
    {"token": "1m", "timeframe_ns": 60000000000},
    {"token": "5m", "timeframe_ns": 300000000000},
    {"token": "15m", "timeframe_ns": 900000000000}
  ]
}
```

**Guarantees**:

1. **Never empty.** The source timeframe is always present, whatever
   `CHANNELFLOW_TIMEFRAMES` says.
2. **Ascending by `timeframe_ns`**, one entry per token.
3. **Exactly the offered set**: each entry's token is either the source or a
   token `CHANNELFLOW_TIMEFRAMES` names, and every such token is present.
4. **Durations are the resampler's.** The `timeframe_ns` values come from the
   same `channelflow.timeframes` table [[REQ-WP-073]] produces bars with, so a
   client that requests a reported duration gets the series the producer
   built.
5. **Refusals happen at startup, not here.** A typo or a calendar period in
   `CHANNELFLOW_TIMEFRAMES` refuses the API process at startup with the
   parser's message; this route never returns a malformed list.

## Configuration

| variable | meaning |
|---|---|
| `CHANNELFLOW_TIMEFRAMES` | comma-separated tokens the resampler builds; the offered set is this plus `1m`. Unset means the source alone. |

The API reads it through `channelflow.timeframes.parse_list` and
`settings_from_env`, the same way `resample_main` does. `.env` is one value for
both processes; `docker-compose.yml` passes it to each.

## Failure modes

| condition | behavior |
|---|---|
| `CHANNELFLOW_TIMEFRAMES` names an unknown token | process refuses to start, naming the token and what is known |
| it names a calendar period (`1M`, `1y`) | process refuses to start, naming the calendar problem |
| it is unset | valid: the response is `[{token: "1m", ...}]` |
| it is empty or only commas | process refuses to start (`parse_list` refuses an empty list) |

## What this route deliberately does not do

- **No `default` field.** The default is a property of a link, not of a
  deployment; the frontend owns it in one constant.
- **No `at`/`as_of` parameter.** It returns configuration, not history; there is
  nothing point-in-time about it.
- **No expansion of calendar periods.** A month has no duration to report.
