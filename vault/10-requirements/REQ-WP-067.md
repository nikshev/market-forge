---
id: REQ-WP-067
title: The targets are measured under load, and a target nobody measured says so
type: work-package
prd_ref: "§36, §45 Phase 8"
prd_lines: "6034-6052, 6904-6913"
phase: 8
status: implemented
depends_on: [REQ-WP-057, REQ-WP-064, REQ-WP-066]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "load tests" and its acceptance states the condition
that matters:

    load tests demonstrate §36's targets, and a target that is not met is
    reported rather than omitted

[[REQ-WP-057]] measured §36's targets on one machine, one call at a time, and
found fifty to several thousand times of headroom. **Nothing drives concurrent
traffic**, and until [[REQ-WP-064]] and [[REQ-WP-066]] there was nothing to
drive it at.

### One call at a time is a different question

A p95 over sequential calls says what one user waits for. It says nothing about
what happens when twenty wait together, and the shape between them is the whole
point of a load test: a system can hold a target at one client and miss it at
ten without anything in the code changing.

§36 states no concurrency, so asserting a made-up one would be a research
default wearing a decision's clothes. What is reported instead is the **shape** —
the measured percentile at each concurrency, and the point at which a target
stops being met — which is the same choice [[REQ-WP-057]] made when it asserted
a scaling ratio rather than an absolute duration.

### A failed request is not a fast one

A request that errors returns sooner than one that works. Folded into the same
samples it lowers the percentile, so a system that is failing measures as a
system that is fast. Errors are counted apart, and **a run with errors is not a
pass** however good its latency looks.

### A target nobody measured must not vanish

The acceptance says an unmet target is reported rather than omitted. The sharper
form is that a target with **no measurement at all** must appear too, saying so.
A report listing two of §36's targets and passing is indistinguishable from one
that measured all three, and the missing one is exactly where the problem would
be.

## Acceptance

- A driver issues requests at a stated concurrency and reports the percentile,
  the error count and the number of requests that produced them.
- The report covers every target in `TARGETS`: met, not met, or not measured —
  each said in so many words, and none omitted.
- A run containing any error is not a pass, whatever the latencies were.
- The measured shape across concurrencies is reported, so where a target stops
  being met is visible rather than inferred.
- The load tool runs against a real deployment, deliberately, the way the
  capture tools do; what runs in CI is the harness, at a size that measures the
  runner honestly and says so.
- Nothing in the report is a number nobody can reproduce: the concurrency, the
  request count and the target are on every line.

## What the first run found

Run against the stack described in `docs/deployment.md`, eleven hours after
[[REQ-WP-066]]'s daemon started:

    concurrency  1: p50  3612ms  p95  4431ms  errors 0
    concurrency  4: p50  6107ms  p95  6649ms  errors 0
    concurrency 16: p50 19130ms  p95 20207ms  errors 0

    chart_historical_load: not met at concurrency 16 — p95 20.2s against 2s
    signal_after_bar_close: not measured
    feature_update: not measured

**§36's target is missed at one client**, let alone sixteen: 4.4 seconds against
a budget of two. [[REQ-WP-057]] measured the same operation at 42ms.

The cause is measured, not guessed: the table holds **654 snapshots and 654 data
files for 657 rows**, and reading it takes 6.9 seconds — about ten milliseconds
per object, which is what a small-file read over an object store costs.

It is [[REQ-WP-066]]'s doing. That daemon commits once a minute while producing
one bar a minute, so every bar became its own file. `BarSink`'s own docstring
says what that does — "a commit per bar would make the snapshot chain as long as
the series" — and `FLUSH_INTERVAL_NS` quotes it before setting an interval equal
to the bar's.

Fixing it is not this requirement: the flush policy and table maintenance are a
change with their own design, and this one's job was to find it. The finding is
recorded on Phase 8 rather than left in a report nobody re-reads.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-108-load-generation]]
- **Tests:**
    - `tests/unit/perf/test_load.py::test_a_failed_request_is_not_a_fast_one`
    - `tests/unit/perf/test_load.py::test_a_missed_target_is_reported_with_its_numbers`
    - `tests/unit/perf/test_load.py::test_a_run_where_everything_failed_has_no_latency_to_report`
    - `tests/unit/perf/test_load.py::test_a_run_with_errors_is_not_a_pass_however_fast`
    - `tests/unit/perf/test_load.py::test_a_target_nobody_measured_is_reported_as_such`
    - `tests/unit/perf/test_load.py::test_an_empty_report_is_not_a_pass`
    - `tests/unit/perf/test_load.py::test_an_unmeasured_line_still_states_the_promise`
    - `tests/unit/perf/test_load.py::test_an_unmeasured_target_is_not_a_pass`
    - `tests/unit/perf/test_load.py::test_every_line_carries_what_reproduces_it`
    - `tests/unit/perf/test_load.py::test_every_request_is_timed_separately`
    - `tests/unit/perf/test_load.py::test_fewer_requests_than_workers_is_refused`
    - `tests/unit/perf/test_load.py::test_the_workers_actually_run_together`
    - `tests/unit/perf/test_load.py::test_the_worst_concurrency_decides`
- **Code:**
    - `src/channelflow/perf/load.py`
    - `tools/perf/load_test.py`
- **Outcomes:** [[OUT-2026-09-14-implement-load-generation]]
<!-- trace:end -->

## Notes

This is Phase 8's last entry. Closing it makes the phase `implemented`.
