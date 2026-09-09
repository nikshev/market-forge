# Implementation Plan: Nothing trains on an unchecked dataset

**Branch**: `us-007-leakage-gate` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One value object that cannot exist unless the leakage checks passed, and three
training entry points that take it instead of a fold list.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `dataset.leakage`, unchanged. Nothing new.

**Testing**: pytest, over 120 constructed rows.

**Target Platform**: `src/channelflow/dataset/`, with signature changes in
`turning/` and `research/`.

**Constraints**: FR-002 and FR-006 are the requirement.

**Scale/Scope**: 1 module, 3 signatures, 9 tests, plus every existing caller.

## Constitution Check

- **I (no look-ahead)** — this is the enforcement of it at the dataset boundary.
- **IV (no ML layer before leakage tests pass)** — Principle IV says the tests
  must pass before the layer is added; this makes them pass before each fit.
- **XIV** — traces to REQ-US-007.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/dataset/
├── certified.py   # NEW: the dataset a model is allowed to see
└── leakage.py     # unchanged -- the checks are REQ-WP-017's

src/channelflow/turning/direct.py       # takes a certificate
src/channelflow/turning/experiment.py   # takes a certificate
src/channelflow/research/ablation.py    # takes a certificate
```

**Structure Decision**: the certificate lives with the dataset, not with the
models. It is a statement about data; putting it beside the estimators would
make it a modelling concern that a new estimator could forget.

## Approach

**The check becomes the only way to obtain the thing training accepts.** Every
check REQ-US-007 needs already existed and already ran — in tests, by hand,
wherever someone chose to call them. That is not a guarantee, and the failure it
misses is silent: a leaked dataset trains fine and scores well.

**No back door.** `CertifiedDataset.__post_init__` refuses an unclean report, so
a hand-assembled certificate is not a way around the checks. A gate with a back
door is documentation.

**The certificate holds its folds.** Training reads them from it rather than
from the caller, so a caller who certifies and then edits their own list cannot
train on something the certificate does not describe.

**The signature test is over `inspect.signature`.** A fifth training entry point
added later fails that test by existing, rather than by someone remembering to
add it to a list.

## Complexity Tracking

> Every existing caller of the three entry points changed. That is the cost of
> making the precondition a type rather than a convention, and it is paid once.
