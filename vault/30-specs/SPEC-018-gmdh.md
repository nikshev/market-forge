---
id: SPEC-018-gmdh
requirement: REQ-WP-018
speckit_path: specs/018-gmdh/spec.md
status: draft
---

## Summary

PRD §23's GMDH layer: a model protocol, a layered polynomial search selected by
an external criterion, complexity budgets, interaction export, and the
comparison report §23.6 requires.

Constitution Principle IV is why this exists now rather than earlier — it
forbids an ML layer until deterministic baselines exist and leakage tests pass,
and [[REQ-WP-019]] supplied the baseline while [[REQ-WP-017]] and the
[[REQ-NRT-A]]..[[REQ-NRT-E]] tests supplied the proof.

[[ADR-030]] keeps the external criterion external: fit and selection take
separate splits, and overlapping ones are refused before anything is fitted.
[[ADR-029]] records that four of §23.6's six baselines do not run, and that
every report names them rather than implying the list was satisfied.

## Links

- Requirement: [[REQ-WP-018]]
- Decisions: [[ADR-029]], [[ADR-030]]
- Consumes: [[REQ-WP-017]]
- Gated by: [[REQ-PRIN-006]]
