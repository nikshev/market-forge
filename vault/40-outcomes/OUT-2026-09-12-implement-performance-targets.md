---
id: OUT-2026-09-12-implement-performance-targets
step: implement
records: [REQ-WP-057]
commit: null
---

## What was done

`channelflow/perf/targets.py`, `tests/perf/` measuring §36's targets against the
real paths, `tests/unit/perf/` measuring the measurement, and a mutation
specification. 27 tests, 9 of 9 mutants caught.

## Measuring first changed what was worth asserting

    chart historical load, 2,000 bars    p95   26ms   against 2,000ms   77x
    RollingOLS / Huber channel fit       p95  0.3ms   against 2,000ms   7,300x
    Quantile channel fit (the slowest)   p95  1.3ms   against 2,000ms   1,500x
    Kalman channel fit                   p95 0.06ms   against 2,000ms   32,600x
    a feature update                     p95  4.7µs   against 1,000ms   214,000x

Between seventy and two hundred thousand times of headroom. That points two ways
at once:

**Asserting §36's targets is right and is not enough.** They are the promise made
to a user, so a test that would notice them breaking is worth having — and with
seventyfold headroom it would keep passing through a fortyfold regression.

**Asserting a tight threshold measures the runner.** The spread between the
fastest and slowest read *within a single run on one machine* was 2.32×. A
threshold close enough to today's number to catch a regression fails on a busy
runner, and a failure nobody can tell from noise is a test people learn to
re-run.

## So the assertion that earns its place is about scaling

Measured: the read costs about 9µs a row, and each doubling takes 1.76 and 1.88
times as long. A change making it quadratic passes a two-second threshold at two
thousand bars and falls over at twenty thousand.

A ratio between two measurements taken in the same run on the same machine
divides that machine out. The bound is three, between linear's two and
quadratic's four, and the guard is demonstrated **in both directions**: a
deliberately quadratic operation measures 5.09× and 4.58× and is refused; a
deliberately linear one measures 2.01× and 2.12× and passes.

The second half is what makes it credible. A bound low enough to refuse
everything would pass the quadratic case and look like a working guard.

## The sweep found the instrument untested

Nine mutations to the measurement arithmetic left **six survivors**. Every
assertion in `tests/perf/` is about the code under measurement; none was about
the percentile, the headroom or the guard clauses. The percentile could have
been a mean, the p95 a p50, the headroom inverted — and the numbers would have
come out confident, plausible and wrong.

That is this repository's recurring failure arriving through the instrument
rather than the subject, and it is the kind a measurement harness is especially
prone to: the output is a number nobody has an independent expectation for.

`tests/unit/perf/` now measures the measuring. Among the things it pins down: a
percentile is a sample that actually happened, a p95 over nineteen fast runs and
one slow one is not the mean, and the same series on a machine ten times slower
gives the same ratios.

## And the spec named a suite it did not run

The mutation specification listed `tests/perf` and the new tests live in
`tests/unit/perf`, so three survivors persisted until both were named. The
harness's own docstring makes the point — a mutation to a shared module is only
honestly measured against every suite that exercises it — and it applied to the
harness's own specification.

## What is still open

- **Nothing keeps the measurements.** Headroom is reported per run and
  discarded, so a slow drift is visible only to somebody comparing two runs by
  eye.
- **§36's other targets**, each for a reason rather than by omission: the
  Telegram target times a call [[ADR-018]] made the caller's, and the symbol and
  level counts are capacities rather than latencies.
- **A load test in the usual sense**, which needs something deployed to load.
