---
id: SPEC-019-adaptive-stops
requirement: REQ-WP-020
speckit_path: specs/019-adaptive-stops/spec.md
status: draft
---

## Summary

PRD §44A's adaptive stop engine: §44A.16's filter pipeline, where every filter
may only hold or tighten and the accepted initial-risk contract has the last
word, and §44A.28's counterfactual replay against naive baselines.

[[ADR-031]] closes PRD §41 rule 9 — realized R is net of fees and modelled
slippage, taken from the first executable price. The rule had been deferred
twice, both times because no economic evaluation existed for costs to be
included in; this is the first one.

[[ADR-032]] makes a hold a proposal like any other. Six different holds look
identical downstream if the policy returns nothing, and in a replay that is the
difference between a policy being careful and a policy being broken.

## Links

- Requirements: [[REQ-WP-020]], [[REQ-BIAS-009]]
- Decisions: [[ADR-031]], [[ADR-032]]
- Consumes: [[REQ-WP-006]], [[REQ-WP-011]], [[REQ-WP-013]], [[REQ-WP-019]]
