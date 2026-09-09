# Implementation Plan: OFI incremental value

**Branch**: `exp-004-ofi-incremental` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module holding EXP-004's taxonomy, arms and increments over
[[REQ-US-006]]'s ablation, plus the channel features it needs as a baseline —
registered for the first time.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `research.ablation` for the scoring. Nothing new.

**Testing**: pytest, over 120 constructed rows; one test runs a subprocess.

**Target Platform**: `src/channelflow/research/`, `src/channelflow/channels/`.

**Constraints**: FR-009 (cold registry), FR-010 (one scoring path).

**Scale/Scope**: 2 modules, 17 tests including the channel features'.

## Constitution Check

- **VI (every feature is documented)** — the channel's four numbers are now
  registered, which PRD §19 has required since before they were consumed.
- **IV (no ML layer before deterministic baselines)** — the scoring is the
  direct logistic baseline, unchanged.
- **XI (results are reproducible)** — one input, one report.
- **XIV** — traces to REQ-EXP-004 and REQ-PRIN-008.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/channels/features.py             # NEW: PRD 19 registration
src/channelflow/research/ofi_incremental.py      # NEW: arms and increments
src/channelflow/research/ablation.py             # + injectable taxonomy
src/channelflow/features/__init__.py             # + channels in the enumeration
```

**Structure Decision**: the channel features live with the channels, not with
the experiment. They are consumed by the score, the panel and the dataset; a
registration reachable only from a research module would be documentation of
something the rest of the system uses without it.

## Approach

**The taxonomy is injectable rather than global.** EXP-004 slices the registry
more finely than [[REQ-US-006]] does — L1 imbalance, the multi-level book, OFI
and wall persistence are four claims, not one family — and both vocabularies
still refuse the other's names, so an arm cannot quietly measure a group its
experiment does not define.

**Membership is prefixes over the registry**, not a hand-kept list, so a feature
added to the book module joins its arm without anyone editing this file.

**Resolution imports the producers first.** The registry fills on import, and
reading it cold showed every order-flow family as empty — a fault invisible
inside a test suite where other files do the importing, so one test runs a fresh
process.

**One scoring path.** A second would make EXP-004's numbers incomparable with
every other experiment's.

## Complexity Tracking

> No violations.
