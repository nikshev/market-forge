# Implementation Plan: Forecast corridor calibration

**Branch**: `exp-009-corridor-calibration` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module measuring three corridor constructions forward from every fit, plus
the raw slope every channel baseline needed to project a forecast at all.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.channels`. Nothing new.

**Testing**: pytest, over deterministic series including one with a regime
change and one with a single shock.

**Target Platform**: `src/channelflow/research/`, one field in
`src/channelflow/channels/models.py`.

**Constraints**: FR-002 (project along the slope), FR-008 (no self-calibration).

**Scale/Scope**: 1 module, 1 snapshot field, 13 tests.

## Constitution Check

- **I (no look-ahead)** — the conformal method calibrates only on errors already
  observed, and a test pins the instant at which its width may react.
- **X (thresholds are configuration)** — the target coverage is the caller's,
  restricted to §13.8's levels.
- **XI (results are reproducible)** — no sampling anywhere.
- **XIV** — traces to REQ-EXP-009.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/corridor_calibration.py   # NEW
src/channelflow/channels/models.py                 # + slope_log_per_bar
src/channelflow/channels/{rolling_ols,huber,quantile,kalman}.py  # set it
```

**Structure Decision**: the raw slope became a snapshot field rather than a
recomputation here. PRD §13.7's forecast centre needs it and
`slope_normalized` cannot serve — it is divided by the residual spread, so two
channels with the same normalized slope move at different speeds. [[ADR-049]]
named this gap when EXP-001 had to measure coverage against a flat band.

## Approach

**Stable means every fold.** A corridor covering 95% in one window and 65% in
another averages to 80%, and pooling would report that as success.

**No winner when nothing holds.** The narrowest corridor among those that miss
their target is still one that does not cover what it claims.

**The conformal method sees only past errors.** The loop records each error
*after* using the window, and the per-instant measurements are public so a test
can pin the instant its width may first react.

**The quantile channel's slope is converted back to per-bar.** It fits on a
centred, scaled index, so its raw slope is per scaled unit — reported as-is it
would have been eighteen times too small.

## Complexity Tracking

> No violations.
