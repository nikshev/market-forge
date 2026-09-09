---
id: OUT-2026-09-09-plan-defi-confluence
step: plan
records: [REQ-EXP-015]
commit: null
---

## What was done

One module, twelve generated arms. 9 tasks.

## What was decided

- **The arms are generated, not listed.** A hand-written list of twelve is a
  list somebody edits, and the property that makes them strict is invisible in
  it.
- **Scoring is [[REQ-WP-019]]'s direct baseline**, reached through the existing
  `run_ablation`. A second scoring path would make these numbers incomparable
  with every other experiment's.
- **Not a `basis_` prefix for the DEX basis family.** The registry's `basis_bps`
  is PRD §16's perp-spot basis, a CEX derivatives feature.

## What is still open

- Nothing from this step.
