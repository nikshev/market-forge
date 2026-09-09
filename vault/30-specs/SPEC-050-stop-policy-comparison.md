---
id: SPEC-050-stop-policy-comparison
requirement: REQ-EXP-017
speckit_path: specs/050-stop-policy-comparison/spec.md
status: draft
---

## Summary

EXP-017 compares seven position-management policies on the exact same immutable
entry signals, reports twelve primary metrics for each, ablates the full engine
seven ways, and is required to be able to conclude `NO_EDGE`.

Three phrases in that requirement do the work. **"The exact same immutable entry
signals"** — every policy replays the same positions over the same paths, and
the entry set carries a fingerprint so two reports cannot be put in one table
without the claim being checkable. **Twelve metrics**, because widening a stop
improves four of them at once and destroys risk control; the premature-stop rate
is a property of the object that carries realized expectancy, which is PRD
§44A.29's warning made structural rather than repeated. **`NO_EDGE`** — the
engine is the arm everybody wants to keep, so the burden is on it: it has to
beat the best of the six simpler policies, itself excluded, by a declared floor.

An ablation here changes what the policy can see, not the policy's code. A
capability the engine does not have cannot veto and cannot supply a level, so
removing it is exactly removing what it contributed — and a branch inside the
policy would be a second policy that only looked like the first.

Four of the twelve metrics are properties of the walk from entry to exit rather
than of the exit, and [[REQ-WP-020]]'s replay is the only place holding the path
and the position's side together. It records them now ([[ADR-052]]), which also
connected `data_quality_ok` from the price point to the policy for the first
time — §44A.18's freeze had never been able to fire in a replay.

## Links

- Requirement: [[REQ-EXP-017]]
- Decision: [[ADR-052]]
- Builds on: [[REQ-WP-020]], [[REQ-BT-001]], [[REQ-WP-019]]
