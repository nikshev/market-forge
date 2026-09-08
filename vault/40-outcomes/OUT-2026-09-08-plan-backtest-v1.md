---
id: OUT-2026-09-08-plan-backtest-v1
step: plan
records: [REQ-WP-010]
commit: null
---

## What was done

Three modules: `runner.py` drives the production engine over bars, `report.py`
holds what a run produced, `__init__.py` exports both. No strategy logic of its
own — that is the requirement, not a style preference.

## What was decided

- **The parity test is the design.** PRD §25.2 forbids a separate backtest
  implementation of strategy logic. Rather than assert that by reading the
  source, the plan drives the live engine and the replay over the same bars and
  demands the same transitions.
- **Refitting the channel at every bar is O(n·lookback) and stays that way.**
  PRD §0.14 puts correctness before performance; an incremental fit is an
  optimisation worth making once there is something to measure.

## What is still open

- Nothing from this step.
