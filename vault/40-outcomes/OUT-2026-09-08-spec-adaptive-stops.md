---
id: OUT-2026-09-08-spec-adaptive-stops
step: spec
records: [REQ-WP-020, REQ-BIAS-009]
commit: null
---

## What was done

`specs/019-adaptive-stops/spec.md`: five user stories, 18 functional
requirements, 10 success criteria, two ADRs.

## What was decided

- **PRD §41 rule 9 is closed here** ([[ADR-031]]). It had been deferred twice —
  [[ADR-009]] scoped economic metrics out of the backtest, [[ADR-024]] left the
  rule at `draft` because nothing produced a number for costs to enter. This
  work package's acceptance requires realized R, so an economic evaluation
  exists, and the rule applies to it now rather than later.
- **A hold is a proposal** ([[ADR-032]]). Returning `None` would satisfy
  §44A.39's "policy may conclude that leaving the stop unchanged is optimal"
  and quietly defeat its "every movement has a structural anchor and reason
  codes", because six different holds look identical downstream.
- **`AnchorKind` has no price-only member.** §44A.39 forbids a blind
  price-following path in the default policy; an enumeration that cannot
  express one enforces it better than a comment does.
- **Scope is the "Done when" list, not the eighteen implementation steps.**
  §44A.39 is explicit that live mode needs a separate execution-security and
  reconciliation acceptance process, so items 16 to 18 are out.

## What is still open

- **Slippage is modelled, not measured.** A constant basis-point cost
  understates a gap and overstates a calm fill; the honest version needs the
  order book at stop time, and no fill model exists.
- **DeFi and cross-venue context (§44A.15)** needs REQ-WP-014/015 and
  REQ-WP-016.
- **§44A.26's ML research targets are not built**, and §44A.39 says they are
  not required for correctness.
