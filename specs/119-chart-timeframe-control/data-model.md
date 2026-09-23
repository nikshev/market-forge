# Phase 1 Data Model: The timeframe is chosen on the chart

No table changes. This is one read of configuration, one response shape, and
the frontend's view state.

## `offered(configured)` — the offered set

```python
def offered(configured: Sequence[Timeframe]) -> tuple[Timeframe, ...]
```

The union of the source timeframe (`SOURCE_TOKEN`, `1m`) and the configured
targets, de-duplicated by token, sorted by `ns`.

| input | result |
|---|---|
| `()` (variable unset) | `(1m,)` |
| `(5m, 15m, 1h)` | `(1m, 5m, 15m, 1h)` |
| `(1m, 5m)` — someone listed the source | `(1m, 5m)` |

**Why the source is unconditional.** §5.1 names `1m` first among the Phase 1
timeframes and the ingest daemon always produces it; `CHANNELFLOW_TIMEFRAMES`
names what resampling builds and excludes the source by design. Listing `1m`
again is harmless and yields the same set, not a duplicate: the union
de-duplicates, so two spellings of one deployment behave identically — the same
rule `parse_list` already follows.

## `TimeframeOut` and `TimeframesResponse` — the read

```text
GET /api/v1/timeframes

200 {
  "timeframes": [
    {"token": "1m", "timeframe_ns": 60000000000},
    {"token": "5m", "timeframe_ns": 300000000000},
    ...
  ]
}
```

| field | type | meaning |
|---|---|---|
| `token` | `str` | the configured spelling, as `parse_list` preserves it |
| `timeframe_ns` | `int` | the duration §28.2's `timeframe_ns` parameter takes |

**Validation**:

- The list is never empty: `offered` includes the source.
- Ascending by `timeframe_ns`, one entry per token.
- No `timeframe_ns` is a `bool` and none is zero or negative — guaranteed by
  `Timeframe.__post_init__`, restated here because the response is where a
  wrong value would become visible to a reader.

There is no `default` field. The default is a link concern (which token a link
with no `tf` opens at), settled in one frontend constant; serving it would be a
second place the default is written.

## The frontend's view state

| value | type | meaning |
|---|---|---|
| `offered` | `TimeframeOption[] \| null` | what the API reported; `null` until it arrives, with a distinct failure state |
| `timeframe` | `string` | the **in-force token**, initialised from the link's `tf` or `DEFAULT_TIMEFRAME` |
| `mode` | `ChannelMode` | existing; gains address synchronisation |

```ts
interface TimeframeOption { token: string; timeframeNs: number }
```

**`matchTimeframe(offered, token)`** returns the option whose `token` equals
`token` exactly, or `null`. Exact match, no normalisation: `"1H"`, `"1m "` and
`"01h"` are each a different token from the deployment's, and quietly accepting
them would be a silent substitution with extra steps.

**`DEFAULT_TIMEFRAME = "15m"`** — the single place the default is written. The
parser uses it for a link with no `tf`, and nothing else repeats it.

## States the page can be in

| state | when | what renders |
|---|---|---|
| link absent | path is not `/chart/:venue/:symbol` | the existing "Open a chart at" message; no requests |
| offered loading | the set request is in flight | existing loading presentation; no bars request |
| offered failed | the set request failed | `LoadState` `failed` with the detail; no chart |
| refused | the in-force token is not in `offered` | `role="alert"` naming the token and listing the offered tokens; **no chart, no bars request** |
| loading | bars request in flight | existing loading presentation |
| empty | the chosen timeframe's series is empty | `LoadState` `empty`, chart drawn with no candles — a quiet market, not a failure |
| ok | bars returned | chart at the in-force timeframe |
| failed | bars request failed | `LoadState` `failed` with the detail; never drawn as empty |

`refused` is deliberately its own presentation rather than a `LoadState` kind:
it is about the question the page was asked, not about a load that failed. It
exists before any request, and rendering the chart alongside it would draw the
empty chart that FR-011 reserves for "no data at the right timeframe".

## Where each value lives

```text
CHANNELFLOW_TIMEFRAMES ─┬─> resample_main   (targets to build)
                        └─> Settings.timeframes ─> GET /api/v1/timeframes
                                                        │
link ?tf ───────────────────────────────────────────────┼─> matchTimeframe ─> in-force ns
DEFAULT_TIMEFRAME ──────────────────────────────────────┘
                                                            │
history.replaceState <── control change <── TimeframeControl
```

One configuration value feeds both producers of the set; one constant defines
the default; one match function decides whether the link can be honoured.
