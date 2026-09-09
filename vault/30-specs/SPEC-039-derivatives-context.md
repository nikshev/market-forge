---
id: SPEC-039-derivatives-context
requirement: REQ-EXP-006
speckit_path: specs/039-derivatives-context/spec.md
status: draft
---

## Summary

EXP-006's four conditionals — funding z-score, OI change, liquidation imbalance,
basis — over [[REQ-BT-001]]'s economics, one variable at a time.

Two decisions carry the weight. Buckets come from declared edges rather than the
sample's quantiles, because quantiles move with the window and the same funding
reading would land in different buckets depending on what else was in it. And a
variable no observation carries is reported unavailable rather than becoming one
bucket holding everything — rendered that way, "no data" and "no relationship"
are indistinguishable.

Every report says whether it is point-in-time or contemporaneous, and the flag
has no default. EXP-014 names that trap for its own subject — "avoid confusing
contemporaneous explanation with forecast value" — and it applies to every
conditional study here.

## Links

- Requirement: [[REQ-EXP-006]]
- Criteria derived: `docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`
- Builds on: [[REQ-WP-013]], [[REQ-BT-001]]
