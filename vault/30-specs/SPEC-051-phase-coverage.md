---
id: SPEC-051-phase-coverage
requirement: REQ-PHASE-0
speckit_path: specs/051-phase-coverage/spec.md
status: draft
---

## Summary

PRD §45's eleven phases are roll-ups: each lists deliverables that other
requirements build. No validator rule reads a roll-up, so a phase's status was
an opinion — and all eleven sat at `draft`, three of them because the PRD states
no acceptance criteria for them at all.

Those three now carry derived criteria, each line naming the PRD section it
comes from, and the derivation records what was deliberately left out. That
retires the last of the ten `ACCEPTANCE-NOT-SPECIFIED` markers — retires, not
abolishes: re-run the extractor over a section with no criteria and the marker
comes back, and a scan makes its return loud.

Every phase note now carries two lists. `covers:` names the requirements that
deliver it; `not_delivered:` names the deliverables nothing does. A test reads
both: a covering requirement must exist and have reached `implemented`, and a
phase claiming to be implemented must have an empty gap list.

All eleven phases are `planned`, and that is the finding rather than a
compromise. The survey behind the gap lists found something missing in every
single one — a virtual clock in Phase 0, chart markers in Phase 1A, a model
registry in Phase 7, the whole of Phase 8. A phase is its deliverables.

## Links

- Requirements: [REQ-PHASE-0, REQ-PHASE-1, REQ-PHASE-1A, REQ-PHASE-2, REQ-PHASE-3, REQ-PHASE-4, REQ-PHASE-5, REQ-PHASE-6, REQ-PHASE-7, REQ-PHASE-7A, REQ-PHASE-8]
- Derivation: `docs/superpowers/specs/2026-09-09-phase-acceptance-design.md`
