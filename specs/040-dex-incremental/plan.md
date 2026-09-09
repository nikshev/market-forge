# Implementation Plan: DEX incremental value

**Branch**: `exp-007-dex-incremental` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

EXP-007's taxonomy and arms over the cumulative machinery extracted from
[[REQ-EXP-004]], plus the instrument the PRD names.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `research.cumulative`, itself over
`research.ablation`. Nothing new.

**Testing**: pytest, over 120 constructed rows carrying DEX-shaped features.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-002 (not run is not zero), FR-007 (the divergence prefix).

**Scale/Scope**: 1 new module, 1 extraction, 9 tests.

## Constitution Check

- **VI (every feature is documented)** — the four unavailable arms carry the
  reason, and a test asserts that state so it cannot change silently.
- **XI (results are reproducible)** — one input, one report.
- **XIV** — traces to REQ-EXP-007.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/cumulative.py       # NEW: extracted from EXP-004
src/channelflow/research/ofi_incremental.py  # now a taxonomy over it
src/channelflow/research/dex_incremental.py  # NEW: EXP-007's taxonomy
```

**Structure Decision**: the shape moved to `cumulative.py` before the second
experiment used it. Two copies of "each arm contains the previous and adds one
family, and here is the difference" would drift, and the two experiments'
increments would stop meaning the same thing.

## Approach

**The membership prefixes are declared for features that do not exist yet.**
When the DEX features are registered, the arms start running without anyone
editing this module — and a test that currently asserts they are empty fails and
says what to update.

**`basis_` is not a DEX prefix.** The registry's `basis_bps` is PRD §16's
perp-spot basis, a CEX derivatives feature, and matching it would have reported
a CEX number's contribution as the DEX view's.

**The instrument is required.** EXP-007 names ETH; a DEX result is about a pool.

## Complexity Tracking

> No violations.
