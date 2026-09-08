---
id: SPEC-007-channel-baseline
requirement: REQ-WP-006
speckit_path: specs/007-channel-baseline/spec.md
status: draft
---

## Summary

Baseline A from PRD §13.2: rolling OLS on log close, bands from empirical
residual quantiles, a normalized slope and a quality score. The hard invariant
`source_max_event_time <= as_of` is enforced in the model rather than left to
callers.

Two definitions the PRD names but never gives are settled in [[ADR-007]].

## Links

- Requirement: [[REQ-WP-006]]
- Decision: [[ADR-007]]
- Consumes: [[REQ-WP-005]]
