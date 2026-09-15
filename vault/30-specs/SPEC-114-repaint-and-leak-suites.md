---
id: SPEC-114-repaint-and-leak-suites
requirement: REQ-NRT-REPAINT
speckit_path: specs/114-repaint-and-leak-suites/spec.md
status: draft
---

## Summary

PRD §35.3 and §35.4 hold today in spot checks and are enumerated by nothing. The
spec makes both mechanical: every channel model's stored snapshots are compared
against deep copies taken when they were produced — which a refit cannot do —
and every registered feature is computed twice, over a truncated input and a
full one. A model or a feature added later without a case is a red suite rather
than a widening gap.

## Links

- Requirement: [[REQ-NRT-REPAINT]]
- Requirement: [[REQ-NRT-LEAK]]
