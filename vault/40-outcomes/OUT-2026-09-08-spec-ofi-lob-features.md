---
id: OUT-2026-09-08-spec-ofi-lob-features
step: spec
records: [REQ-WP-011, REQ-PRIN-008]
commit: null
---

## What was done

`specs/011-ofi-lob-features/spec.md`: five user stories, 20 functional
requirements, 9 success criteria, three ADRs.

## What was decided

- **The spec traces REQ-PRIN-008 as well** ([[ADR-015]]). PRD §19 requires
  every feature to be registered and Principle VI says an undocumented feature
  is not done; that constraint has sat at `draft` since extraction because
  nothing produced a feature until now. The registry is enforced by a test —
  the exposed set and the registered set must be equal, with no field blank —
  so adding a feature without registering it fails the suite by name.
- **CVD-price divergence is not built** ([[ADR-013]]). §15.4 names it among
  five features and defines the other four. Sign disagreement, normalized slope
  difference, correlation breakdown and swing divergence all give different
  numbers, and whichever was implemented would become the definition by
  accident. The gap stays legible in the registry.
- **The executed/cancelled split is stated as a rule, not a heuristic**
  ([[ADR-014]]): executed is bounded by what actually traded at that price, and
  the remainder is cancellation. The bias is towards reporting cancellation,
  which under PRD §2.2's warning is the safer error — a pulled wall read as
  absorbed demand is the failure that costs money.
- **Scope is REQ-WP-011's acceptance list, not all of §15.** §15.5's
  cumulative-depth slope, convexity, depth concentration and liquidity-gap
  features, and §15.7's absorption, are named in the PRD but not in this work
  package's acceptance criteria. The distance is deliberate and recorded.

## What is still open

- **REQ-WP-006's channel quality submetrics stay unregistered.** They predate
  the registry; backfilling them would mean re-opening a merged requirement.
  ADR-015 records that the work is owed.
- **§15.5's remaining shape features and §15.7's absorption have no
  requirement note.** Like §35.3/§35.4 for rule R5, this is deferred
  requirement extraction rather than a decision to skip them.
