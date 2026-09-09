---
id: OUT-2026-09-09-plan-channel-comparison
step: plan
records: [REQ-EXP-001]
commit: null
---

## What was done

One research module, two small enabling changes, 10 tasks.

## What was decided

- **The first two models are one fitter under two width options.** PRD §13.2
  lists both and prefers the second; a separate class would duplicate the fit to
  change three lines. The model name still differs, so nothing compares a model
  with itself under two labels.
- **The runner takes a `ChannelModel` protocol.** Typed to baseline A, the
  comparison would have needed its own runner — and §25.2's rule against a second
  backtest implementation would be broken by the experiment meant to use it.
- **The runner's configuration block reads the model's own fields** instead of
  baseline A's named parameters, so a run with the Kalman filter does not report
  quantiles it never used.

## What is still open

- Nothing from this step.
