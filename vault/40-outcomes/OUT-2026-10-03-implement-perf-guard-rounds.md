---
id: OUT-2026-10-03-implement-perf-guard-rounds
step: implement
records: [REQ-INFRA-011]
commit: 3b33a7e
---

## What was done

`channelflow.perf.targets` gained `timed_interleaved` (one run of every operation per round, the start
rotating, results in the order given), `timed` and it take an injectable `clock`, and `scaling_ratio`
takes the quantile it compares (median by default, so existing callers are unchanged). The three scaling
tests in `tests/perf/test_targets.py` now measure in rounds and compare the lower quartile. The targets,
the thresholds and the bound of three are untouched.

**RED, as run:** `ImportError: cannot import name 'timed_interleaved' from 'channelflow.perf.targets'`.

**After:** `tests/unit/perf` 45 passed (12 new). In the fake-clock world a perfectly linear operation with
a burst covering exactly one size gives a sequential ratio above 3 (the fault, reproduced
deterministically) and rounds-ratios all between 1.5 and 3, wherever the burst falls (five positions); a
quadratic operation still gives ratios of at least 3, with and without the burst.

**Live evidence** (three scaling tests, 20 runs each, same host, load average 4-5): old method 1 failure
quiet and 2 under four CPU hogs; new method **0 in 40**. That is evidence and not proof — a failure rate
on a shared host is itself noisy, and 3 of 40 against 0 of 40 would not survive a significance test. The
proof is the deterministic test.

## What was decided

- **Rounds and a lower quantile; not a wider bound, not retries, not leaving the tests out of the hook.**
  A wider bound blunts the guard; a retry hides a failure instead of removing its cause; and a check absent
  from the commit hook would have to be present in CI, which is no quieter.
- **One commit for requirement, spec, plan, tasks and implementation.** The ladder gives each its own
  commit, and every commit must pass the gate this requirement exists to repair: six gates or full runs had
  failed in a session, each a ten-minute retry. The artifacts all exist and are in the same commit; the trace is
  unchanged, the granularity is not.

## What is still open

- The other timing tests (the targets, with fiftyfold headroom) are not changed and were not the ones failing.
- Whether the lower quartile is enough on a host busier than this one: unknown; the fake-clock test says
  what rounds can and cannot cancel.
