# Implementation Plan: Lookback sensitivity

**Branch**: `exp-002-lookback-sensitivity` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module: the six-lookback sweep over [[REQ-EXP-001]]'s comparison machinery,
a plateau finder, and a recommendation that structurally cannot be the peak.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `research.channel_comparison` for the per-lookback
measurement. Nothing new.

**Testing**: pytest. The plateau logic is tested on hand-built sweeps, where a
value can be placed exactly where it needs to be.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-007 and FR-009 — the rule EXP-002 states in one line.

**Scale/Scope**: 1 module, 14 tests.

## Constitution Check

- **X (thresholds are configuration)** — the tolerance is an argument with a
  named research default.
- **XI (results are reproducible)** — the plateau tie-break is declared, so one
  sweep gives one recommendation.
- **XIV** — traces to REQ-EXP-002.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/lookback_sensitivity.py   # NEW
```

**Structure Decision**: `find_plateau` and `recommend` are separate public
functions, not steps inside the sweep. The sweep takes seconds and the rule
takes microseconds; separating them means the rule — which is the whole
experiment — is tested on constructed sweeps where a value sits exactly where
the test needs it.

## Approach

**The recommendation cannot be the peak.** Not by convention: `recommend`
returns `None` when there is no plateau, and the peak is reported in its own
field so a reader can see the two differ. A default that reached for the peak
when no plateau existed would break the rule exactly where it matters.

**An absent value breaks a plateau.** Skipping it would join two runs across a
lookback nobody could measure, producing a plateau that exists only in the
report.

**The centre, not the edge.** An edge of a plateau is one noisy neighbour away
from being off it, and the centre is the furthest point from either.

**A run of one is not a plateau.** It is the peak under another name.

## Complexity Tracking

> No violations.
