# Implementation Plan: Turning-point baselines and the GMDH derivative experiment

**Branch**: `wp-019-derivative-experiment` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/turning/`: the direct baseline REQ-WP-019's
fourth criterion asks for, PRD §13A.11's forward path and its derivative roots,
§13A.12's stability gate — which is Test F — and the experiment that ties them
together and is allowed to conclude `NO_EDGE`.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: NumPy, already present. `channelflow.dataset` for
rows and folds, `channelflow.models` for the baselines and GMDH.

**Storage**: none.

**Testing**: pytest, pure. Fixtures are constructed paths whose roots are known
by hand, and a labelled row set with a target that has no signal by
construction.

**Target Platform**: `src/channelflow/turning/`.

**Constraints**: FR-008 and FR-011 ([[ADR-041]]), FR-012 ([[ADR-042]]), FR-015
(no clock, no RNG).

**Scale/Scope**: 4 modules, one added method on `GMDHNetwork`.

## Constitution Check

- **I (no look-ahead)** — the path's coefficients are label-side and the spec
  says so; features come from `Row`, which enforces the separation itself.
- **IV (no ML layer before deterministic baselines and leakage tests)** — this
  is the reason the whole feature waited: REQ-WP-019's structural baseline and
  REQ-WP-017's leakage tests both exist now.
- **X (thresholds are configuration)** — §13A.12's three metrics carry the
  PRD's research defaults on a configuration object, and the PRD's own words
  that they are research defaults travel with them.
- **XI (results are reproducible)** — the perturbation lattice is deterministic,
  so a stability assessment repeated is a stability assessment reproduced.
- **XIV** — traces to REQ-WP-019 and REQ-NRT-F.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/turning/
├── __init__.py
├── direct.py      # the direct target's baseline over walk-forward folds
├── path.py        # PRD 13A.11's cubic path, derivatives, roots
├── roots.py       # 13A.12's stability metrics and promotion gate (Test F)
└── experiment.py  # the end-to-end experiment, and its verdict

src/channelflow/models/gmdh.py   # + predict(), the unclipped output

tests/unit/turning/
├── test_direct.py
├── test_path.py
├── test_roots.py
└── test_experiment.py
```

**Structure Decision**: `path.py` holds no model and no data — given four
coefficients it answers where the derivative is zero, and that answer is
checkable against a hand-solved quadratic. Keeping it free of the fitting makes
the arithmetic testable on its own, which matters because every later refusal is
built on it being right.

## Approach

**`GMDHNetwork` gains `predict`, and `predict_proba` becomes it plus a clip.**
The network already fits by least squares against a continuous target; only the
probability accessor clipped. A forward path clipped to `[0, 1]` is not a
forward path, and the alternative — a second network class — would duplicate the
search to change one line.

**The perturbation lattice is deterministic** ([[ADR-041]]). §13A.12 says
"bootstrap/ensemble members"; either answers the stability question, and a
lattice answers it the same way twice. Principle XI is not negotiable and an RNG
seed is an argument about reproducibility rather than an instance of it.

**`NO_EDGE` is a return value, never an exception** ([[ADR-042]]). REQ-WP-019's
fifth criterion is about the product not being blocked by a research result, and
an exception is precisely a research result that blocks. Every path that ends in
"no edge" — too little data, no root, no root that survives, no improvement on
the base rate — returns the same shape of answer carrying its reason.

**The gate refuses with names.** A promotion that fails reports which of
§13A.12's conditions failed, because "rejected" alone sends the reader back to
recompute what the gate already knew.

## Complexity Tracking

> No violations.
