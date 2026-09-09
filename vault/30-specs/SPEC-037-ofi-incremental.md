---
id: SPEC-037-ofi-incremental
requirement: REQ-EXP-004
speckit_path: specs/037-ofi-incremental/spec.md
status: draft
---

## Summary

EXP-004's five cumulative arms — channel only, then L1 imbalance, the
multi-level book, OFI and wall persistence — over [[REQ-US-006]]'s ablation,
with the difference between neighbours reported as the increment each family
added.

Two things had to change. The ablation's taxonomy became injectable, because
EXP-004 slices the registry more finely than US-006's four groups do and both
vocabularies must still refuse the other's names. And the channel's four numbers
were registered as features for the first time: PRD §19 has required it since
before they were consumed by the score, the panel and the dataset, and every arm
here rests on them as a baseline.

## Links

- Requirement: [[REQ-EXP-004]]
- Criteria derived: `docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`
- Builds on: [[REQ-US-006]], [[REQ-WP-011]], [[REQ-PRIN-008]]
