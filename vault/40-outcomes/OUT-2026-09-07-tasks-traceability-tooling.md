---
id: OUT-2026-09-07-tasks-traceability-tooling
step: tasks
records: [REQ-INFRA-001]
commit: null
---

## What was done

Wrote `specs/001-traceability-tooling/tasks.md`: 17 tasks in three phases —
mark the five verifying tests (T001-T005), mark the seven implementing
source files (T006-T012), then close the loop (T013-T017: status
transitions, `make graph`/`make validate`/`make test`, the outcome note, and
the idempotence check).

A cross-check of `spec.md`, `plan.md` and `tasks.md` against each other (the
analysis `/sdd-tasks` calls for) found:

## What was decided

- **Consistent**: every FR/SC the tasks reference (FR-001, FR-002, FR-003,
  FR-005, FR-006, SC-003) exists in `spec.md`; no task cites a requirement
  the spec doesn't state.
- **Consistent**: the five test files and seven source files tasks.md
  enumerates are exactly the ones plan.md's Project Structure section lists
  under `tools/trace/` and `tests/tools/trace/`.
- **One ambiguity flagged during drafting**: the `/sdd-implement` command's
  usual test-first phrasing ("write the failing tests first... confirm the
  new tests fail for the right reason") does not literally apply here.
  T001-T005 mark pre-existing, already-passing tests; there is nothing to
  watch fail first, because the behavior they test was implemented in
  Tasks 4-10, before this exercise began. T013 is worded to say so directly
  rather than describing a step that cannot literally happen.
- No duplication or under-specification found between the three documents.

## What is still open

- T001-T012 (the marking work) have not been applied to the actual test and
  source files yet — that happens next, directly against
  `tools/trace/*.py` and `tests/tools/trace/*.py`.
- Status remains `planned`; task breakdown does not advance it per the
  `/sdd-tasks` command's own rule.
