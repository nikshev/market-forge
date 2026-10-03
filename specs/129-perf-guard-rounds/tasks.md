---
description: "Tasks for REQ-INFRA-011 — a scaling guard measures its sizes under the same conditions"
---

# Tasks: A scaling guard measures its sizes under the same conditions

**Tests**: written first, run RED. Marker `@pytest.mark.trace("REQ-INFRA-011")`.

- [x] T001 Write `tests/unit/perf/test_interleaved.py` (fake clock; sequential fooled; rounds not fooled wherever the burst falls; quadratic still caught; rotation; order; refusals; the quantile). Run it RED: `ImportError: cannot import name 'timed_interleaved'`
- [x] T002 Add `timed_interleaved`, the `clock` parameter on `timed`, and `fraction` on `scaling_ratio` in `src/channelflow/perf/targets.py`; export from `channelflow.perf`. The 45 perf unit tests pass
- [x] T003 Move the three scaling tests in `tests/perf/test_targets.py` to rounds and `SCALING_QUANTILE = 0.25`; correct the module docstring's premise
- [x] T004 Compare failure counts of the old and the new measurement, repeated, quiet and under four CPU hogs, and record them
- [x] T005 `make lint`, `make typecheck`, `make test`; `make graph && make validate`; commit

## Coverage

| requirement | task |
|---|---|
| FR-001 rounds | T001, T002 |
| FR-002 `fraction` | T001, T002 |
| FR-003 fake-clock fault and fix | T001 |
| FR-004 quadratic still caught | T001, T003 |
| FR-005 three tests moved | T003 |
| FR-006 targets and bound unchanged | T003 |
| SC-003 failure counts | T004 |
