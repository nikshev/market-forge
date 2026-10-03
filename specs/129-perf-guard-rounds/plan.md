# Implementation Plan: A scaling guard measures its sizes under the same conditions

**Branch**: `129-perf-guard-rounds` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

## Summary

Add `timed_interleaved` to `channelflow.perf.targets`, give `timed` an injectable clock, give
`scaling_ratio` a `fraction` (default the median), and move the three scaling tests to rounds and the
lower quartile. A fake-clock world makes the fault exact: it is tested before it is fixed.

## What planning measured

- **The premise is in the code's own docstring** ("a ratio between two measurements from the same run
  divides the machine out"); nothing there says the measurements must interleave.
- **Sizes were measured in blocks** (`timed` per size, then the next), the read test with only 7 samples.
- **The failures were all in tests of this shape** — `test_the_read_stays_linear_as_the_series_grows` and
  `test_a_linear_operation_passes_the_same_guard` — and none in the target tests, which have fiftyfold
  headroom.
- **Run alone they pass**: the read test 4 of 4 and the linear test 3 of 3 while the load average was 3.5-4.
- **Under CPU contention** (four busy loops), before the change: 2 failures in 20 runs of the three tests;
  quiet but loaded: 1 in 20. After: 0 in 40.

## Decisions, and what each rejected

**D1. Rounds, with a rotating start.** One run of every size per round. Rejected: more samples per size (a
longer burst still lands on one size); a wider bound (blunts the guard); retrying a failed test (hides the
failure rather than removing its cause); excluding the tests from the commit hook (a check present in
neither gate, which `CLAUDE.md` forbids, and the CI runner is no quieter).

**D2. The lower quartile.** Noise only adds time. Rejected: the minimum, which is one lucky sample and
so noisy in the other direction.

**D3. A fake clock in the tests.** `timed` and `timed_interleaved` take a `clock`, defaulting to
`perf_counter_ns`, so the fault can be reproduced exactly instead of waited for.

## Project Structure

```text
src/channelflow/perf/targets.py  __init__.py     # the change
tests/unit/perf/test_interleaved.py              # 12 tests, fake clock
tests/perf/test_targets.py                       # three tests moved to rounds
```

## Constitution Check

Principle XII (correctness precedes performance) is the one engaged: the guard exists to protect it, and
this makes it trustworthy. No principle is violated; Complexity Tracking is empty.
