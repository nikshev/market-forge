# Contract: `channelflow.timeframes` and `channelflow.pipeline.resample`

This feature exposes no new HTTP route. §28.2's `GET /api/v1/bars` already takes
`timeframe`, and this work makes more values of that parameter return data. The
contracts below are module boundaries.

## `channelflow.timeframes`

```python
TIMEFRAMES: Mapping[str, Timeframe]     # the known tokens
SOURCE_TOKEN: str = "1m"                # what every target is built from

def parse(token: str) -> Timeframe
def parse_list(text: str) -> tuple[Timeframe, ...]
def window_start(t_ns: int, timeframe: Timeframe) -> int
```

**`parse`**

- A known token returns its `Timeframe`.
- `1M`, or any calendar-defined period, raises `CalendarPeriod` with a message
  naming the reason. This is the single place that refusal lives.
- An unknown token raises `UnknownTimeframe` naming the token and listing what
  is known. It never returns `None` and never falls back to a default: a typo in
  configuration must be loud.

**`parse_list`**

- Splits on commas, trims, ignores empty segments.
- An empty result raises rather than returning an empty tuple: a deployment
  configured to produce no timeframes is a mistake that looks like a quiet
  market.
- Preserves neither order nor duplicates — returns them sorted by `ns` and
  de-duplicated, so two spellings of one configuration behave identically.

**Guarantee**: `window_start` is total over `int` and never raises. For any `t`
and `T`, `window_start(window_start(t, T), T) == window_start(t, T)`.

## `channelflow.pipeline.resample`

Pure. No clock, no catalog, no IO — the shape `archive.py` and `builder.py`
already hold, and for their reason.

```python
def resample(
    source: Sequence[Bar],
    *,
    target: Timeframe,
    source_timeframe: Timeframe,
    already_present: AbstractSet[int],
    now_ns: int,
) -> ResampleResult
```

**Inputs**

- `source` — one venue and symbol's bars at `source_timeframe`, any order.
- `already_present` — `open_time_ns` values already stored for this target. The
  caller reads them; this function does not know a table exists.
- `now_ns` — supplied, never read from a clock. A window whose `close_time_ns`
  is greater than `now_ns` is still in progress: not written, not refused.

**Output** — `ResampleResult(bars, refusals, skipped)`:

- `bars` — complete, closed windows not in `already_present`, in `open_time_ns`
  order, every one with `is_final=True`.
- `refusals` — closed windows whose source bars were incomplete.
- `skipped` — how many closed complete windows were already present.

**Guarantees**

1. **Idempotent.** With `already_present` containing every `open_time_ns` from a
   previous result, `bars` is empty and `skipped` accounts for all of them.
2. **Never partial.** A window appears in `bars` only if exactly
   `target.ns // source_timeframe.ns` source bars fall inside it.
3. **Never early.** No bar has `close_time_ns > now_ns`.
4. **Order-independent.** Shuffling `source` changes nothing in the output.
5. **Total.** An empty `source` gives an empty result, not an error.
6. **Refuses a non-multiple.** `target.ns % source_timeframe.ns != 0` raises
   before any window is considered, because such windows cannot tile the source.

**Non-guarantee, stated**: `resample` does not check that `source` really is at
`source_timeframe`. The caller filters by `timeframe_ns` when it reads. A
mislabelled input would produce wrong bars, which is why the caller's filter is
part of the tested path rather than a convention.

## `channelflow.pipeline.resample_main`

The only file that knows a loop and a catalog exist.

```text
python -m channelflow.pipeline.resample_main [--once] [--loop 5m]
```

- Reads `CHANNELFLOW_TIMEFRAMES` through `channelflow.timeframes.parse_list`.
- For each configured `(venue, symbol, target)`: reads the source series and the
  target's existing open times, calls `resample`, appends through `BarSink`.
- Prints one `ResampleReport.line` per series, and every refusal, to stdout —
  the visibility FR-005 requires. A refusal that only incremented a counter
  would be as silent as the bug it replaces.
- Exit code is zero when every series was processed, whether or not anything was
  written. A pass that wrote nothing because everything existed is success.
- One series failing does not end the pass, the rule `maintenance_main` already
  follows: the failure is printed, named, and the remaining series are done.
