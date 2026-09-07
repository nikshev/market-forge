---
description: "Task list for REQ-INFRA-002 CI full gate"
---

# Tasks: CI runs the full gate

**Tests**: Included for the local half. The workflow half is verified by a real
run — see plan.md's Constitution Check for why no unit test can prove it.

## Phase 1: Mark integration tests

- [x] T001 Register an `integration` marker in `pyproject.toml` alongside `trace`, and confirm it does not interfere with `@pytest.mark.trace` (FR-008).
- [x] T002 Mark both tests in `tests/integration/test_dev_stack.py` with `@pytest.mark.integration`, keeping their existing trace markers.

## Phase 2: Fast gate (US1)

- [x] T003 Add a `test-fast` target to the `Makefile` running `pytest -m "not integration"` (FR-007).
- [x] T004 Change `.pre-commit-config.yaml`: replace the `make validate` hook with `make test-fast`, so the hook needs no container runtime (FR-006). Keep the ruff hooks unchanged.
- [x] T005 Verify SC-001 and SC-002 by hand with the stack stopped: a documentation commit succeeds; a commit breaking lint is rejected; a commit breaking a non-integration test is rejected.

## Phase 3: Full gate (US2)

- [x] T006 Create `.github/workflows/ci.yml`: trigger on push and pull_request; `ubuntu-latest`; PostgreSQL and MinIO as job services with pinned image tags matching `docker-compose.yml`; environment from the same defaults as `.env.example` (FR-001, FR-002).
- [x] T007 Give the workflow four separately named steps — lint, typecheck, test, validate — so a failure names which one (FR-003, FR-004, FR-005).
- [x] T008 Create the MinIO bucket in the workflow before the tests run, matching what `make up` does locally.

## Phase 4: Close the loop

- [x] T009 Verify FR-009 and SC-005 by comparing the two lists explicitly: every check the local hook stopped running appears in the workflow. Record the comparison, do not assert it.
- [x] T010 Document the two gates in `CLAUDE.md`: what runs locally, what runs in CI, and that CI is where `implemented` is earned (FR-010).
- [x] T011 Push and observe a real workflow run. Record its result and URL in the implement outcome note (SC-003). If it fails, fix and re-run — an unobserved workflow is an unverified one.
- [x] T012 Verify SC-004 by deliberately breaking an integration test on a scratch branch, confirming the workflow fails and names it, then discarding the branch.

## Notes

`REQ-INFRA-002` will have `VERIFIES` edges only from the local-half tests. Its
CI half is evidenced by an observed run recorded in the outcome note. That
asymmetry is real and is stated in the plan rather than hidden behind a test
that merely parses YAML.
