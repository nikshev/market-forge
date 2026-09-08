---
id: OUT-2026-09-08-spec-backtest-v1
step: spec
records: [REQ-WP-010]
commit: null
---

## What was done

Specified REQ-WP-010 as `specs/009-backtest-v1/spec.md`: 13 functional
requirements, 7 success criteria.

## What was decided

- **No returns, and the reason is not squeamishness.** PRD §25.5 lists twenty
  metrics; almost all need an outcome definition (§40) and a fill model (§25.4),
  neither built. §41 rule 9 requires fees and slippage in any economic
  evaluation. A gross win rate would be quoted as the win rate, because a caveat
  does not travel with a number. [[ADR-009]].
- **The report will look thin next to §25.5, and that is the point.** The gap
  between what it reports and what the PRD wants is the visible measure of what
  is unbuilt. Filling it with computable-but-meaningless figures would hide that.
- **Strategy reuse is proven by parity, not by inspection** (FR-005, SC-001).
  PRD §25.2 says to avoid a separate backtest implementation; §35.5 asks for
  replay parity. Rather than assert the property by reading code, the backtest is
  run against the live engine driven directly over the same bars and the
  candidate histories compared transition for transition. A divergence is the
  two implementations having drifted apart.
- **Skipped bars are reported, not silently zero** (FR-011, SC-006). A run whose
  history is too short to fit a channel produces no candidates — and "no setups
  found" and "we could never look" are very different results wearing the same
  number.
- **The report names its own configuration** (FR-009). PRD §13.11 calls the zone
  bounds research defaults; two runs whose reports cannot be told apart are two
  runs whose difference cannot be attributed.

## What is still open

- **Event replay** (§25.1) needs the order-book service and microstructure
  features. Bar replay only here.
- **Costs, fills, returns and walk-forward** — §25.3, §25.4, §25.5, §25.7 — all
  wait on outcome definitions.
- **Loading bars from storage.** The backtest consumes what it is given; §29.4's
  table does not exist.
