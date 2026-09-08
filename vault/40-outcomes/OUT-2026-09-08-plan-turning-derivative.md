---
id: OUT-2026-09-08-plan-turning-derivative
step: plan
records: [REQ-WP-019, REQ-NRT-F]
commit: null
---

## What was done

Four modules under `src/channelflow/turning/`, one added method on
`GMDHNetwork`, four test files, 13 tasks.

## What was decided

- **`path.py` holds no model and no data.** Given four coefficients it says
  where the slope is zero, and that answer is checkable against a hand-solved
  quadratic. Every refusal downstream is built on it being right.
- **`GMDHNetwork` gains `predict`, and `predict_proba` becomes it plus a clip.**
  The network already fits a continuous target by least squares; only the
  accessor clipped. A forward price path squashed into `[0, 1]` is not a path,
  and a second network class would duplicate the search to change one line.
- **The fitting/selection split is declared by the caller**, chronologically.
  ADR-030 has `GMDHNetwork.fit` refuse to invent it, because choosing it is what
  PRD §41 rules 1 and 10 are about; the experiment names its rule instead of
  hiding it.
- **A coefficient that never varies is not learned.** Fitting a network to
  reproduce a constant would report a search that found structure where the path
  simply has a lower degree.

## What is still open

- Nothing from this step.
