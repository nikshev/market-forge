# Phase 0: Research — Channel production for the running deployment

**Feature**: `specs/122-channel-production/spec.md` | **Requirement**: [[REQ-WP-077]]

## Decisions

### D1: Follow the `resample_main.py` pattern for the loop

**Decision**: The new `channel_main.py` mirrors `resample_main.py`'s shape exactly: `--once` default, `--loop <interval>` to repeat, `argparse` for arguments, one pass function per series.

**Rationale**: The pattern is already proven in production (`resample_main` runs the stack's resampler). It is the established way to run a periodic pass in this codebase. A new pattern would add a novel risk for no benefit.

**Alternatives considered**:
- A `worker` container running a general task queue: rejected — unnecessary abstraction for a single periodic pass
- Integration into `maintenance_main`: rejected — maintenance removes; channel production produces; hiding a producer inside a remover is what [[ADR-055]] and the compose comments explicitly guard against

### D2: Discover series from the `bars` table, not from configuration

**Decision**: The pass discovers `(venue, symbol)` pairs by querying the `bars` table for the source timeframe, rather than reading a symbol list from `.env`.

**Rationale**: A configured symbol list can disagree with what the bars table actually holds — the same failure mode `resample_main.py` already solves by discovery. The resampler discovers from the source series; the channel producer does the same.

**Alternatives considered**:
- Read `CHANNELFLOW_INGEST_SYMBOLS` again: rejected — that list is for the ingest daemon; the deployment may have bars from other sources and the configured list would be incomplete

### D3: Reuse `record_replay` unchanged

**Decision**: `channelflow.pipeline.replay.record_replay` is called as-is; no modifications to the function itself.

**Rationale**: The spec explicitly states `record_replay` is "correct and tested; this feature only wires it into a scheduled loop" (Assumptions). Modifying it would break the guarantee the spec relies on and require re-testing the whole replay path.

**Alternatives considered**:
- Create a thin wrapper that re-implements the call: rejected — the wrapper is a copy-paste risk; the function already has the right signature

### D4: One `CHANNELFLOW_CHANNEL_INTERVAL` for the loop frequency

**Decision**: A single environment variable `CHANNELFLOW_CHANNEL_INTERVAL` (default `5m`, using the same grammar as `CHANNELFLOW_RESAMPLE_INTERVAL`) controls how often the pass repeats.

**Rationale**: Consistency with `resample_main.py`'s `CHANNELFLOW_RESAMPLE_INTERVAL` and `maintenance_main`'s `--loop` grammar. The operator learns one spelling for "how often does a loop run".

**Alternatives considered**:
- Separate variables per timeframe: rejected — over-engineering; the interval is a freshness knob, not a correctness one

### D5: Add a `worker` service to `docker-compose.yml`

**Decision**: Add a `worker` service using the same `Dockerfile` as the API, running `python -m channelflow.pipeline.channel_main --loop ${CHANNELFLOW_CHANNEL_INTERVAL}`.

**Rationale**: The same image pattern as `ingest-binance` and `resample`. PRD §6.2 names `worker` and it exists as code now.

**Alternatives considered**:
- Running channel production inside the API container: rejected — a web server should not also run background loops; the compose comments for `ingest-binance` and `resample` both establish this pattern

### D6: Use `bars_table.read_bars` to discover series and read bars

**Decision**: `run_pass` queries `bars_table.read_bars(table, timeframe_ns=source_ns)` to find series, then passes each series to `record_replay`.

**Rationale**: Consistent with `resample_main.py`'s discovery pattern. The function is already tested and the bars table holds exactly the data we need.

**Alternatives considered**:
- Iterate over all venues × symbols from settings: rejected — the configured list can be incomplete; discovery from the table is the established pattern

### D7: Per-series failure isolation matching `resample_main.py`

**Decision**: Wrap `record_replay` in a `try/except` per series, printing the failure with venue/symbol/timeframe and continuing.

**Rationale**: The spec explicitly requires this (FR-006, US5). The `resample_main.py` pattern (`"  {venue} {symbol} {target.token}: FAILED — ..."` and `continue`) is the already-validated implementation.

**Alternatives considered**:
- Collect all failures and report at end: rejected — same outcome but delayed reporting

## Unresolved items

None. All technical decisions are resolved by referencing existing, proven code.

## Notes

The research phase found no unknowns — every question the plan might have asked is answered by existing code in `resample_main.py`, `record_replay`, and `bars_table.read_bars`. This is the expected outcome: the spec correctly identifies that the missing piece is only a loop, not an algorithm.
