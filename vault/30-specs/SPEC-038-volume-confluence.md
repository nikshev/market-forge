---
id: SPEC-038-volume-confluence
requirement: REQ-EXP-005
speckit_path: specs/038-volume-confluence/spec.md
status: draft
---

## Summary

EXP-005 is the one experiment in the set that asks a yes/no question, and the
word it turns on is "materially". An effect size chosen after seeing the
difference is not a finding, so it is a required argument with no default —
asserted over the function's signature, because a default would be that
judgement made by whoever wrote the module.

The answer has three values and the third is a real one: most confluence claims
are "not materially different", and a study that could only say higher or lower
would say one of them.

The classification is PRD §14.1's "node overlap with channel boundaries", which
[[REQ-WP-012]]'s `nodes_at` already answers, plus the value-area edges EXP-005
names beside the nodes.

## Links

- Requirement: [[REQ-EXP-005]]
- Criteria derived: `docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`
- Builds on: [[REQ-WP-012]], [[REQ-BT-001]]
