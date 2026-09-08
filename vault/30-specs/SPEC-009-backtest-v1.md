---
id: SPEC-009-backtest-v1
requirement: REQ-WP-010
speckit_path: specs/009-backtest-v1/spec.md
status: draft
---

## Summary

Bar replay through the production signal engine on a virtual clock, reporting
signal-quality metrics. [[ADR-009]] scopes returns out: an economic figure
without the costs PRD §41 rule 9 requires would be quoted without its caveat.

Strategy reuse is proven by parity against the live engine rather than asserted
by reading the code.

## Links

- Requirement: [[REQ-WP-010]]
- Decision: [[ADR-009]]
- Consumes: [[REQ-WP-005]], [[REQ-WP-006]], [[REQ-WP-007]]
