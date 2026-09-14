---
id: OUT-2026-09-14-implement-load-generation
step: implement
records: [REQ-WP-067]
commit: null
---

## What was done

`perf/load.py`, `tools/perf/load_test.py`, and a run against the live stack. 13
tests, **11 of 11 mutants caught**.

## It found a real defect on its first run

Eleven hours after [[REQ-WP-066]]'s daemon started:

    concurrency  1: p95  4431ms
    concurrency  4: p95  6649ms
    concurrency 16: p95 20207ms

    chart_historical_load: not met — p95 20.2s against a 2s budget
    signal_after_bar_close: not measured
    feature_update: not measured

§36's target is missed **at one client**. [[REQ-WP-057]] measured the same
operation at 42ms against a local catalog; this is the deployment.

Cause, measured rather than guessed: **654 snapshots and 654 data files for 657
rows**, and a full read takes 6.9 seconds — about ten milliseconds an object,
which is what small files over an object store cost.

**It is mine, from one requirement ago.** The daemon commits once a minute and
produces one bar a minute, so every bar became its own file. `BarSink`'s
docstring says exactly what that does — "a commit per bar would make the
snapshot chain as long as the series" — and I quoted that sentence in the
comment above `FLUSH_INTERVAL_NS` before setting the interval equal to the bar's.
Reasoning about a trap and then walking into it is worse than not seeing it.

Fixing it is a separate requirement: the flush policy and table maintenance are
their own design. Finding it was this one's job.

## Three verdicts, not two

Phase 8's acceptance asks that an unmet target be "reported rather than
omitted". The sharper form is a target with **no measurement at all**: a report
of two targets that passes is indistinguishable from one that measured three.

So `NOT_MEASURED` is a verdict, `passed()` refuses it, and the run above says in
so many words that two of §36's three targets were not measured — because they
are pipeline timings and this tool speaks HTTP. That honesty is the reason the
report is worth reading.

## A failed request is not a fast one

An error returns sooner than work does. Folded into the samples it lowers the
percentile, so a failing system measures as a quick one. Errors are counted
apart, a run with any error is not a pass however good its latencies, and a run
where everything failed raises rather than reporting a zero that would be the
fastest result in the file.

## The worst concurrency decides

A target met at one client and missed at ten is not met. Reporting the best run
would have said it was — and with the numbers above, reporting concurrency 1
would still have failed, which is its own kind of luck.

## What is not closed

Phase 8's load-test entry is delivered. The missed target is now its own entry on
the phase, pointing here, because a phase that closed while one of §36's three
promises is broken would be the omission this requirement exists to prevent.
