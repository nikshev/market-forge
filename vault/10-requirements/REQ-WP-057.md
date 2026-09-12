---
id: REQ-WP-057
title: The performance targets are measured, and the thing that would break them is what is asserted
type: work-package
prd_ref: "§36, §45 Phase 8"
prd_lines: "6034-6052, 6914"
phase: 8
status: implemented
depends_on: [REQ-WP-056, REQ-TBL-001]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "load tests" and never defines them; §36 states the
targets they would be against:

    feature update <= 1s
    signal after bar close <= 2s
    chart historical load p95 < 2s for 2,000 bars

**Measured first, because the numbers change what is worth asserting.** On one
developer machine:

    chart historical load, 2,000 bars    p95   42ms   against 2,000ms
    channel fit, 60-bar window           p95  0.3ms   against 2,000ms
    the slowest of the four models       p95  1.3ms   against 2,000ms

Every target has between fifty and several thousand times of headroom. Two
consequences, and they point in opposite directions:

**A test asserting §36's targets passes trivially, and keeps passing through a
fortyfold regression.** It is not worthless — the targets are the promise made to
a user, and a test that would notice them being broken is worth having — but it
is not a test that would notice anything going wrong before then.

**A test asserting a tight threshold measures the runner, not the code.** Within
a single run on one machine the spread between fastest and slowest read was
already 2.27×; a shared CI runner is worse. A threshold close enough to today's
measurement to catch a regression would fail on a busy runner, and a failure
nobody can distinguish from noise is a test people learn to re-run.

**So the assertion that earns its place is about scaling.** Measured: the read
costs about 9µs a row and doubling the rows takes 1.9 to 2.0 times as long.
A change making it quadratic passes a two-second threshold at two thousand bars
and falls over at twenty thousand — and a ratio between two measurements taken in
the same run on the same machine is something a busy runner cannot move.

## Acceptance

- §36's stated targets are measured against the real code paths, not against
  stand-ins, and the measurement is reported rather than only compared.
- Each target is asserted, so a regression large enough to break the promise
  fails.
- The headroom is reported alongside, so shrinking headroom is visible before it
  becomes a failure.
- Scaling is asserted as a ratio between measurements taken in one run, and a
  quadratic change in the read path fails it while a slow machine does not.
- A test demonstrates the scaling assertion failing on a deliberately quadratic
  implementation, so the guard is known to bite.
- The measurements run in the ordinary suite and need no service beyond a
  temporary warehouse.

## Notes

Human territory. Never machine-rewritten.

**§36's other targets are not measured here**, and each for a reason rather than
by omission. "Telegram delivery attempt <= 3s after signal" times a network call
[[ADR-018]] made the caller's; "3 symbols × 4 timeframes" and "L2 top 50/100
levels" are capacities rather than latencies, and nothing runs long enough to
have a capacity; Phase 2's targets are for a phase that has not started.

**This is not a load test in the usual sense.** Nothing here generates concurrent
traffic against a deployed system, because nothing is deployed
([[REQ-WP-056]] records that gap). What it does is measure the paths a user waits
on and guard the property that would degrade them.
