---
id: REQ-INFRA-002
title: Continuous integration runs the full gate with the dev stack provisioned
type: infrastructure
prd_ref: "§0.9, §0.13"
prd_lines: "23-27"
phase: null
status: implemented
depends_on: [REQ-WP-001, REQ-INFRA-001]
tags: [tooling, ci]
---

## Requirement

The repository's full quality gate — lint, strict type check, the whole test
suite including integration tests, and traceability coverage — runs
automatically on every push and pull request, against a provisioned instance of
the development stack.

The local pre-commit hook runs only the checks that need no external services,
so that committing does not require a running container runtime. Continuous
integration, not the local hook, is where a requirement's `implemented` status
is actually earned.

## Requirement rationale

This exists because of a conflict the pipeline surfaced while implementing
REQ-WP-001, not from the PRD.

REQ-WP-001's `VERIFIES` edges come from integration tests that need live
PostgreSQL and MinIO. `make validate` runs the suite for real — that is what
stops a skipped test satisfying a coverage rule — and the pre-commit hook runs
`make validate`. So with the stack down, the tests fail and the commit is
blocked; and making them skip instead would drop the edges and trip rule R2,
because the tooling deliberately treats "skipped" and "absent" as the same
thing. Both paths block the commit, and the cost grows with every future
requirement whose verification needs a network or a service.

## Acceptance

- A push or pull request to the repository triggers a workflow that provisions
  PostgreSQL and MinIO and runs lint, type check, the full test suite and
  traceability coverage.
- The workflow fails when any of those four fails, and its failure is
  attributable to which one.
- The local pre-commit hook completes without a running container runtime.
- No requirement's verification is silently weakened: any check removed from the
  local hook runs in the workflow instead, and the trade is recorded rather than
  implied.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-003-ci-full-gate]]
- **Tests:**
    - `tests/tools/gates/test_two_gates.py::test_no_check_is_absent_from_both_gates`
    - `tests/tools/gates/test_two_gates.py::test_the_fast_gate_deselects_exactly_the_integration_tests`
    - `tests/tools/gates/test_two_gates.py::test_the_workflow_runs_every_check_of_the_full_gate`
    - `tests/tools/gates/test_two_gates.py::test_the_workflow_runs_the_full_suite_not_the_fast_one`
- **Code:**
    - `.github/workflows/ci.yml`
- **Outcomes:** [[OUT-2026-09-07-implement-ci-full-gate]], [[OUT-2026-09-07-plan-ci-full-gate]], [[OUT-2026-09-07-spec-ci-full-gate]], [[OUT-2026-09-07-tasks-ci-full-gate]]
<!-- trace:end -->

## Notes

Written mid-flight after `/sdd-implement REQ-WP-001` hit the conflict described
above. The alternative considered and rejected was leaving the gate fully local
and accepting Docker as a precondition for every commit — honest, but a cost
that compounds as connector and replay tests arrive.
