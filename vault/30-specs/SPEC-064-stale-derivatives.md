---
id: SPEC-064-stale-derivatives
requirement: REQ-WP-026
speckit_path: specs/064-stale-derivatives/spec.md
status: draft
---

## Summary

PRD §45's Phase 3 states two acceptance criteria. The first holds. The second —
"stale REST polling cannot silently reuse old value" — does not, and the gap is
in the package the criterion names.

`state_at` returns the newest state at or before the instant with no upper bound
on its age. A poll that failed, or a venue that stopped publishing, leaves the
last value in place; funding, open interest and basis then report numbers that
look current, and every score built on them inherits the error without a trace.

The rest of the repository already knows this. `crossvenue` excludes a quote past
its tolerance and names why; `book` and `alerting` guard it; §43's ranker
penalizes it in the score. `derivatives` is the one without it.

Two decisions shape the fix.

**Refusal, not exclusion.** `crossvenue` can exclude a stale quote because it has
others to fall back on. A single state has nothing to fall back to, so the honest
answer is to refuse — and a stale refusal is a different type from an absent one,
because a venue that never published and one that stopped are different facts.

**The z-score's history is untouched.** `funding_z` looks back over many
observations by design. A rule that refused old history would break the feature
the rule exists to protect; what is refused is a stale reading presented as the
value now.

## Links

- Requirement: [[REQ-WP-026]]
- The package it corrects: [[REQ-WP-013]]
- The pattern it follows: [[REQ-WP-016]]'s consensus exclusion
