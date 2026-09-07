---
description: "Task list for REQ-INFRA-001 — dogfood the traceability tooling on itself"
---

# Tasks: Deterministic Traceability Graph and Coverage Validator

**Input**: Design documents from `specs/001-traceability-tooling/`

**Prerequisites**: plan.md, spec.md

**Note**: Written retroactively. The implementation this describes
(`tools/trace/*.py`, `tests/tools/trace/test_*.py`) already existed before
this task list was written; what remained was annotating it with trace
markers so REQ-INFRA-001 itself becomes traceable through it. Tasks below are
the annotation and closure work, not a from-scratch build.

## Phase 1: Verifying tests (write/mark first)

- [ ] T001 [US1] Mark `tests/tools/trace/test_validate.py::test_r5_fails_for_a_planned_constraint_without_a_test`
      with `@pytest.mark.trace("REQ-INFRA-001")` — demonstrates the R5/R2
      independence acceptance criterion directly.
- [ ] T002 [US1] Mark `tests/tools/trace/test_graph.py::test_build_graph_wires_every_edge_kind`
      with `@pytest.mark.trace("REQ-INFRA-001")` — demonstrates FR-001/FR-002
      (every edge kind is wired from its collector).
- [ ] T003 [US2] Mark `tests/tools/trace/test_dashboard.py::test_update_requirement_notes_is_idempotent`
      with `@pytest.mark.trace("REQ-INFRA-001")` — demonstrates FR-006/SC-003
      (regeneration is idempotent and marker-safe).
- [ ] T004 [US1] Mark `tests/tools/trace/test_cli.py::test_validate_exits_one_and_names_the_rule`
      with `@pytest.mark.trace("REQ-INFRA-001")` — demonstrates FR-005 (the
      CLI's exit code is the validator's contract with the pre-commit hook).
- [ ] T005 [US1] Mark `tests/tools/trace/test_pytest_plugin.py::test_parametrized_tests_are_recorded_once_per_case`
      with `@pytest.mark.trace("REQ-INFRA-001")` — demonstrates FR-003
      (parametrized cases counted per case, from pytest's own collection).

## Phase 2: Implementing source (mark after tests are confirmed)

- [ ] T006 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/model.py`.
- [ ] T007 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/collect.py`.
- [ ] T008 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/graph.py`.
- [ ] T009 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/validate.py`.
- [ ] T010 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/dashboard.py`.
- [ ] T011 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/cli.py`.
- [ ] T012 [P] Add `# @trace: REQ-INFRA-001` near the top of `tools/trace/pytest_plugin.py`.
- [ ] T012a [P] Add `# @trace: REQ-INFRA-001` near the top of
      `tools/trace/frontmatter.py`. Missed in the original pass (an eighth
      `tools/trace/*.py` module, not seven) — added during the final
      whole-branch review's fix wave.

## Phase 3: Close the loop

- [ ] T013 Set `REQ-INFRA-001` `status: tested` after T001-T005 are confirmed
      failing-for-the-right-reason-then-passing (they already pass — they are
      pre-existing tests being annotated, not new tests being written), run
      `make graph && make validate`.
- [ ] T014 Run `make test`; confirm the full suite passes with the new markers.
- [ ] T015 Create `vault/40-outcomes/OUT-2026-09-07-implement-traceability-tooling.md`
      with `step: implement`, `records: [REQ-INFRA-001]`.
- [ ] T016 Set `REQ-INFRA-001` `status: implemented`, run
      `make graph && make validate` — R1, R2 and R4 must all be satisfied by
      this point.
- [ ] T017 Run `make graph` a second time and confirm `git status --short`
      reports no changes — the idempotence acceptance criterion (SC-003).

## Dependencies & Execution Order

Phase 1 (T001-T005) before Phase 2 (T006-T012a): a source file's `IMPLEMENTS`
edge is only meaningful once there is at least one `VERIFIES` edge for the
same requirement to point at the same claim. Phase 2 tasks are independent of
each other (`[P]`, different files). Phase 3 is strictly sequential and
depends on both prior phases being complete.
