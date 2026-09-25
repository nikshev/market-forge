# Implementation Tasks: Channels, signals and extrema produced for the running deployment

**Feature**: `specs/122-channel-production/spec.md` | **Requirement**: [[REQ-WP-077]]

## Task List

### Phase 1: Create the channel production module

- [ ] **T01**: Create `src/channelflow/pipeline/channel_main.py`
  - Mirror `resample_main.py` structure: `argparse` with `--once` (default) and `--loop <interval>`
  - Implement `_interval_seconds` helper (copy from `resample_main.py`)
  - Implement `run_series` that calls `record_replay` for one `(venue, symbol, timeframe)`
  - Implement `run_pass` that discovers series from `bars` table and processes each target timeframe
  - Per-series `try/except` with `continue` (failure isolation)
  - Log line per series: `"{venue} {symbol} {timeframe}: channel snapshots: N, signals: M, confirmed extrema: K, extremum candidates: L"`
  - Print failures with venue/symbol/timeframe

### Phase 2: Wire the module into the deployment

- [ ] **T02**: Add `worker` service to `docker-compose.yml`
  - Same `Dockerfile` and storage config as `api`/`ingest-binance`/`resample`
  - Command: `python -m channelflow.pipeline.channel_main --loop ${CHANNELFLOW_CHANNEL_INTERVAL}`
  - Environment: same as `resample` + `CHANNELFLOW_CHANNEL_INTERVAL`
  - Depends on: `postgres`, `minio`, `api` (so bars exist)
  - Restart: `unless-stopped`

- [ ] **T03**: Add `CHANNELFLOW_CHANNEL_INTERVAL=5m` to `.env.example`
  - Place near `CHANNELFLOW_RESAMPLE_INTERVAL` for discoverability
  - Comment explaining it's the channel pass interval

### Phase 3: Tests

- [ ] **T04**: Create `tests/unit/pipeline/test_channel_main.py`
  - Test `_interval_seconds` grammar (same as resample test)
  - Test `run_pass` discovers series from bars table
  - Test `run_series` calls `record_replay` with correct args
  - Test failure isolation: one series fails, others complete
  - Test empty timeframe skipped with log
  - Test idempotence: second pass writes zero new rows (mock catalog)

- [ ] **T05**: Add `@pytest.mark.trace("REQ-WP-077")` to all new tests

### Phase 4: Validation & commit

- [ ] **T06**: Run `make lint`, `make typecheck`, `make test` (fast gate)
- [ ] **T07**: Run `make graph && make validate` (full gate)
- [ ] **T08**: Commit and push

## Dependencies

- T01 before T02, T03 (module must exist)
- T02, T03 before T04 (tests can mock or run with real services)
- T04 before T06 (tests must exist before lint/typecheck validates them)

## Notes

The implementation reuses:
- `record_replay` from `channelflow.pipeline.replay` (already tested, correct)
- `bars_table.read_bars` for discovery (already tested)
- `TIMEFRAMES`, `parse_list`, `SOURCE_TOKEN` from `channelflow.timeframes`
- Settings from `channelflow.settings`

No new abstractions, no new dependencies, no new database schema. This is pure wiring of an existing correct function into a loop.