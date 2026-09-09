# Implementation Plan: Derivatives/DeFi confluence at turning points

**Branch**: `exp-015-defi-confluence` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module turning EXP-015's two adjectives — *strict* and *same
walk-forward folds* — into things the code refuses to run without.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.research.ablation`,
`channelflow.research.cumulative`, `channelflow.dataset`.

**Testing**: pytest, over rows where one family decides the target, a second
duplicates it, and three carry nothing.

**Target Platform**: `src/channelflow/research/`.

**Constraints**: FR-002 (strictness), FR-004 to FR-006 (the folds), FR-003 (the
basis prefix).

**Scale/Scope**: 1 module, 15 tests.

## Constitution Check

- **IV (a number without its baselines is not a result)** — every family is
  measured against the baseline arm and against the full set.
- **VII (live and replay are the same code)** — scoring is [[REQ-WP-019]]'s
  direct baseline, reached through `run_ablation`.
- **XI (results are reproducible)** — the folds come from the certificate and
  are used as given.
- **XIV** — traces to REQ-EXP-015.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/defi_confluence.py   # NEW
```

**Structure Decision**: the arms are generated rather than listed. A hand-written
list of twelve arms is a list somebody edits, and the property that makes them
strict is not visible in it.

## Approach

**Strictness is checked, not asserted.** `strictness_violations` is public
because "strict" is a property nobody can verify by reading a table of numbers:
an arm two families from both references still produces a delta, and the delta
still looks like one family's contribution.

**Two directions, because they disagree.** Added-alone and
removed-from-the-full-set answer different questions whenever families overlap.
The fixture built for this module has one family that duplicates another, and it
reads as helping alone and adding nothing in context — a single-direction
ablation reports whichever of those two facts it happened to measure.

**The fold fingerprint carries the spans, not just the count.** Two studies can
both use three folds over different rows, and a fingerprint that only counted
them would call those the same splits — which is the exact claim it exists to
check.

**Not a `basis_` prefix.** The registry's `basis_bps` is PRD §16's perp-spot
basis, a CEX derivatives feature. Matching it in the DEX family would report a
CEX number's contribution as the DEX view's — the trap EXP-007 walked into.

## Complexity Tracking

> No violations.
