---
id: SPEC-030-ablation
requirement: REQ-US-006
speckit_path: specs/030-ablation/spec.md
status: draft
---

## Summary

REQ-US-006's five arms — channel only, channel + order flow, channel +
derivatives, channel + DEX, all combined — each scored on one shared fold set,
per EXP-015's "use strict ablation and same walk-forward folds".

The load-bearing part is what the report refuses to say. The feature registry
carries order-flow and derivatives features today and no channel or DEX ones, so
"channel + DEX" resolves to the same features as "channel only". Scored, it
returns an identical number, and a reader takes that as evidence the DEX family
adds nothing — a finding about the data pipeline in the clothes of a finding
about the market. So an arm whose family contributed nothing is reported as not
run, with the reason, and never enters the ranking.

That is the same distinction [[ADR-044]] draws in the score and [[ADR-046]]'s
`research_only` draws in the repaint comparison: what the system could not look
at is never reported as what it looked at and found.

## Links

- Requirement: [[REQ-US-006]]
- Builds on: [[REQ-WP-017]], [[REQ-WP-018]], [[REQ-WP-019]]
