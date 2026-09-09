---
id: SPEC-043-lead-lag-value
requirement: REQ-EXP-010
speckit_path: specs/043-lead-lag-value/spec.md
status: draft
---

## Summary

EXP-010 asks one question in one sentence: does cross-venue divergence contain
predictive value after realistic latency and costs. Three words in it are the
whole design.

**Predictive** means out of sample. A threshold chosen on the data it is scored
on always looks profitable, which is why PRD §17.2 forbids turning a correlation
into a rule "without OOS validation" — and this study is that validation.

**Latency** means the divergence is not actionable the instant it appears. The
entry is delayed by a stated number of bars, and the parameter has no default:
"realistic" belongs to whoever runs the study on their own infrastructure.

**Costs** is §41 rule 9, refused before anything is scored.

The verdict is returned, never raised ([[ADR-042]]), and [[ADR-040]]'s import ban
extends here: this module is the evidence, not a licence.

## Links

- Requirement: [[REQ-EXP-010]]
- Criteria derived: `docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`
- Builds on: [[REQ-WP-016]], [[REQ-BT-001]]
