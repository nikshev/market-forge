# Implementation Plan: Rejection detector comparison

**Branch**: `exp-003-detector-comparison` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Two new detectors at [[REQ-WP-007]]'s existing plugin point, and one research
module that runs each through the production machine and reports four metrics.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.signals` for the machine and the
detectors, `channelflow.backtest` for outcomes and economics.

**Testing**: pytest. The detectors are tested on hand-shaped bars; the metrics
on hand-built candidate lives.

**Target Platform**: `src/channelflow/signals/`, `src/channelflow/research/`.

**Constraints**: FR-003 (no second engine), FR-002 (unavailable is not zero).

**Scale/Scope**: 2 detectors, 1 module, 20 tests.

## Constitution Check

- **VII (live and replay are the same code)** — every detector is measured
  inside the production machine.
- **VI (every feature is documented)** — the unavailable detector carries the
  reason it cannot run, in the report.
- **XI (results are reproducible)** — the stateful detector's memory is per-run,
  and the ranking's ties break on name.
- **XIV** — traces to REQ-EXP-003.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/signals/rejection.py             # + WickOnly, TwoBarConfirmation
src/channelflow/research/detector_comparison.py  # NEW
```

**Structure Decision**: the detectors live with the plugin point, not with the
experiment. PRD §21.3 says "implement multiple rejection detectors as plugins",
and a detector that only the experiment can reach is not one.

## Approach

**Measurement is separate from the run.** `detector_metrics` takes candidate
lives rather than bars, because one of the four metrics is unreachable
otherwise: a confirmation the market later takes back is a specific path through
the lifecycle, and no bar series found so far drives the machine down it.
Handing the function the lives that describe one is how that metric is tested
rather than assumed — and the split is honest about which metrics the fixtures
cover.

**The fourth detector is named, not approximated.** Its inputs do not exist at
the interface it would use.

**The stateful detector holds exactly one bar.** That is what "next bar closes
lower" means, and the runner's `deepcopy` keeps it per-run.

## Complexity Tracking

> No violations.
