---
id: OUT-2026-09-09-spec-phase-coverage
step: spec
records: [REQ-PHASE-0, REQ-PHASE-1, REQ-PHASE-1A, REQ-PHASE-2, REQ-PHASE-3, REQ-PHASE-4, REQ-PHASE-5, REQ-PHASE-6, REQ-PHASE-7, REQ-PHASE-7A, REQ-PHASE-8]
commit: null
---

## What was done

`specs/051-phase-coverage/spec.md`: three user stories, 8 functional
requirements, 8 success criteria, over all eleven phases.

## What was decided

- **Two lists per phase**, in frontmatter and in prose: what delivers it and
  what nothing delivers.
- **A phase at `implemented` must have an empty gap list.** A note that lists
  what is missing and claims to be finished is a contradiction nobody spots in
  review and a test spots immediately.
- **The lists are checked by a test, not by a seventh validator rule.**
  `collect_requirements` ignores unknown frontmatter keys, and a rule would mean
  changing the collector, the model and the validator for a relationship only
  eleven notes have. `test_vault_hard_gated.py` is the precedent.

## What is still open

- **Nothing promotes a phase automatically.** When a gap closes, the note has to
  be edited; the test then allows the promotion rather than performing it.
