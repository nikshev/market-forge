---
id: REQ-INFRA-011
title: "A scaling guard measures its sizes under the same conditions"
type: infrastructure
prd_ref: "§36; repository practice"
prd_lines: "0-0"
phase: null
status: implemented
depends_on: [REQ-WP-057]
tags: [performance, tests, flake]
hard_gated: false
---

## Requirement

[[REQ-WP-057]] guards PRD §36's targets with a scaling assertion: a doubling of the work may cost at most
three times as much. Its premise, written into its module docstring, is that "a ratio between two
measurements from the same run divides the machine out".

It does not, when the measurements are taken one after another — twenty runs of the small size, then
twenty of the next, then twenty of the largest. A burst of load a few seconds long lands on one size and
not the others, the ratio across it is wrong by the size of the burst, and the test fails on a code
change that never happened.

Measured on 2026-10-03, on a host with a load average of about four: **six commit gates or full runs
failed in one session**, on two timing tests (`test_the_read_stays_linear_as_the_series_grows` four times,
`test_a_linear_operation_passes_the_same_guard` twice), each green when run alone, each costing a
ten-minute retry. A gate that fails for no reason is a gate people learn
to re-run, which is the failure [[REQ-WP-057]]'s own docstring says it was written to avoid.

The sizes must therefore be measured **in rounds**: one run of every size per round, so that whatever the
machine does reaches all of them, and the ratio between them survives it. And the ratio compares a lower
quantile, because noise only ever adds time.

## Acceptance

- A function measures several operations in rounds, one run of each per round, the starting operation
  rotating, and returns the measurements in the order given.
- With a fake clock and a burst of extra cost over a contiguous range of calls, measuring one size after
  another produces a ratio far from two for a perfectly linear operation (the fault, reproduced), and
  measuring in rounds does not, wherever the burst falls.
- A quadratic operation is still reported as quadratic, with and without a burst: the guard still bites.
- The three scaling tests use it, and a deliberately quadratic operation still fails the guard.
- Under CPU contention the three scaling tests fail less often than they did, counted over repeated
  runs and recorded; the deterministic test above is the proof and the count is evidence.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-129-perf-guard-rounds]]
- **Tests:**
    - `tests/unit/perf/test_interleaved.py::test_a_lower_quantile_ignores_the_slow_half_that_noise_adds`
    - `tests/unit/perf/test_interleaved.py::test_a_quadratic_operation_is_still_caught_when_measured_in_rounds`
    - `tests/unit/perf/test_interleaved.py::test_every_round_runs_every_operation_once`
    - `tests/unit/perf/test_interleaved.py::test_measuring_in_rounds_survives_the_same_burst`
    - `tests/unit/perf/test_interleaved.py::test_measuring_one_size_after_another_is_fooled_by_a_burst_of_load`
    - `tests/unit/perf/test_interleaved.py::test_nothing_to_measure_and_no_runs_are_refused`
    - `tests/unit/perf/test_interleaved.py::test_the_measurements_come_back_in_the_order_they_were_given`
    - `tests/unit/perf/test_interleaved.py::test_the_order_within_a_round_rotates`
    - `tests/unit/perf/test_interleaved.py::test_wherever_the_burst_falls_the_rounds_agree[0]`
    - `tests/unit/perf/test_interleaved.py::test_wherever_the_burst_falls_the_rounds_agree[13]`
    - `tests/unit/perf/test_interleaved.py::test_wherever_the_burst_falls_the_rounds_agree[25]`
    - `tests/unit/perf/test_interleaved.py::test_wherever_the_burst_falls_the_rounds_agree[40]`
    - `tests/unit/perf/test_interleaved.py::test_wherever_the_burst_falls_the_rounds_agree[7]`
    - `tests/unit/perf/test_interleaved.py::test_with_no_noise_a_linear_operation_gives_exactly_two`
- **Code:**
    - `src/channelflow/perf/targets.py`
- **Outcomes:** [[OUT-2026-10-03-implement-perf-guard-rounds]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
