# Implementation Plan: GMDH against the baselines

**Branch**: `exp-008-gmdh-vs-baselines` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Two baselines [[ADR-029]] left out, built so its objections are answered rather
than overruled, and the four metrics EXP-008 asks for beside the Brier score.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: NumPy. No scikit-learn, no LightGBM — [[ADR-050]].

**Testing**: pytest, over constructed matrices including an interaction target.

**Target Platform**: `src/channelflow/models/`.

**Constraints**: FR-002 (no default strengths), FR-004 (a tree that can see an
interaction).

**Scale/Scope**: 3 modules, 19 tests.

## Constitution Check

- **IV (no ML layer before deterministic baselines)** — this strengthens the
  baselines rather than the model.
- **X (thresholds are configuration)** — the regularization strengths are
  required, not defaulted.
- **XI (results are reproducible)** — exhaustive splits and a fixed descent, so
  no seed exists to argue about.
- **XIV** — traces to REQ-EXP-008.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/models/regularized.py   # NEW: elastic net logistic
src/channelflow/models/boosting.py      # NEW: depth-limited boosted trees
src/channelflow/models/metrics.py       # NEW: calibration, PR-AUC, buckets, stability
src/channelflow/models/report.py        # runs four baselines now, names two
```

**Structure Decision**: the metrics live with the models, not with the
experiments. Calibration and PR-AUC are properties of a classifier, and
[[REQ-EXP-013]] needs them too — a copy in each experiment would drift.

## Approach

**Each new baseline answers ADR-029 on its own terms.** The elastic net's
strengths are required arguments, so the coefficient ADR-029 refused to default
is the caller's. The trees are depth-two by default, the shallowest that can
hold an interaction — a stump booster is additive and would be the "poor tree"
ADR-029 warned about.

**PR-AUC rather than ROC-AUC**, because these targets are imbalanced and ROC-AUC
flatters a model that never finds a rare positive.

**Empty calibration bands are omitted.** Scored at zero gap they would make a
model that stayed silent look better calibrated than one that spoke.

**Stability counts only what every fold chose.** A feature that turned up in one
other fold is not a feature the model kept reaching for.

## Complexity Tracking

> The gradient booster is the largest single piece of arithmetic added to this
> repository. It is textbook and says so; [[ADR-050]] records that it is a
> baseline rather than a model, and the dependency question stays open.
