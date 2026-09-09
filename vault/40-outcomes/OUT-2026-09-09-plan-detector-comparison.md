---
id: OUT-2026-09-09-plan-detector-comparison
step: plan
records: [REQ-EXP-003]
commit: null
---

## What was done

Two detectors, one research module, 7 tasks.

## What was decided

- **Measurement separated from the run.** One of the four metrics cannot be
  reached by any bar series tried, so `detector_metrics` takes candidate lives
  and the metric is tested on lives that describe a taken-back confirmation.
- **The stateful detector holds one bar**, which is what "next bar closes lower"
  means; the runner's `deepcopy` keeps that memory per-run.
- **A bodyless bar with a wick is a rejection**, not a division by zero.

## What is still open

- Nothing from this step.
