# Implementation Plan: Causal derivative turning points

**Branch**: `exp-012-derivative-turning` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module comparing four causal slope estimators against labels made
by a centred filter, at four horizons — plus the Protocol fix that let a frozen
transform satisfy the causality guard at all.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.extrema` (the causality guard), numpy.

**Testing**: pytest, over a smooth swing series, a noisy one, and a triangle
with a single labelled turn.

**Target Platform**: `src/channelflow/research/`, with a Protocol correction in
`extrema/causality.py`.

**Constraints**: FR-002 and FR-003 (the centred refusal, from the production
guard), FR-007 (the right edge).

**Scale/Scope**: 1 module, 12 tests.

## Constitution Check

- **I (no look-ahead, ever)** — the whole subject of this module. The labels are
  retrospective and declared so; every candidate is checked by `require_causal`
  before the comparison starts.
- **VII (live and replay are the same code)** — the refusal is the production
  guard's, not a copy.
- **XI (results are reproducible)** — no sampling.
- **XIV** — traces to REQ-EXP-012.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/derivative_turning.py   # NEW
src/channelflow/extrema/causality.py             # Transform: read-only properties
```

**Structure Decision**: the labeller is a first-class object that declares
`centered = True`, rather than a private function with a comment saying not to
use it live. The declaration is what `require_causal` reads; a comment is not.

## Approach

**The guard runs before the comparison, on every candidate.** Not on the one
that looks suspicious, and not as an assertion inside the loop — `require_causal`
is REQ-NRT-D's own function, and the wrapper only adds the method's name to the
message.

**The Protocol was stricter than its own reference implementation.** `Transform`
asked for settable `name` and `centered` attributes, which a frozen dataclass
cannot provide — so `CausalTransform`, the class the module ships as the causal
transform, did not satisfy it. Read-only properties fix that.

**The right edge is what makes a local polynomial causal.** Fitted to the same
window and read at its centre it is the same arithmetic and a forbidden
estimator. Three bars past a peak the two disagree in sign, which is what the
test pins.

**Precision, not recall**, and absent rather than zero when nothing was called.

## Complexity Tracking

> No violations.
