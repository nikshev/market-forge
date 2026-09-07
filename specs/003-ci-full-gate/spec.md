---
traces: [REQ-INFRA-002]
status: draft
---

# Feature Specification: CI runs the full gate

**Feature Branch**: `003-ci-full-gate`

**Created**: 2026-09-07

**Status**: Draft

**Input**: REQ-INFRA-002 — the full quality gate runs automatically against a provisioned dev stack; the local hook keeps only checks that need no external service.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Commit without a container runtime (Priority: P1)

A developer changes a document or a pure-Python module, commits, and the hook
completes — without Docker running, and without being told to start it.

**Why this priority**: This is the pain that produced the requirement. Every
commit currently needs a live stack, and that cost grows with each future
requirement verified by an integration test.

**Independent Test**: Stop the stack, make a trivial change, commit. The hook
passes.

**Acceptance Scenarios**:

1. **Given** no containers running, **When** the developer commits a documentation change, **Then** the hook completes and the commit succeeds.
2. **Given** no containers running, **When** the developer commits a change that breaks lint, **Then** the hook still rejects it — the fast checks are not weakened.
3. **Given** no containers running, **When** the developer commits a change that breaks a non-integration test, **Then** the hook rejects it.

---

### User Story 2 - The full gate runs on every push (Priority: P1)

A push or pull request triggers a workflow that provisions PostgreSQL and MinIO
and runs lint, strict type check, the whole suite including integration tests,
and traceability coverage. A failure in any one is attributable to that one.

**Why this priority**: Equal to US1 and inseparable from it. Removing checks
from the local hook without them running somewhere would weaken verification
silently, which is exactly what this repository exists to prevent.

**Independent Test**: Push a branch whose integration test fails; the workflow
fails and names the failing check.

**Acceptance Scenarios**:

1. **Given** a push to any branch, **When** the workflow runs, **Then** it provisions both services and runs all four checks.
2. **Given** a change that breaks only an integration test, **When** the workflow runs, **Then** it fails and the failure names the test.
3. **Given** a change that breaks traceability coverage, **When** the workflow runs, **Then** it fails with the violated rule.
4. **Given** a workflow run, **When** a developer reads its output, **Then** they can tell which of the four checks failed without reading raw logs end to end.

---

### Edge Cases

- What happens when a service does not become healthy in the workflow? The run must fail with a message naming the service, not hang until the job timeout.
- What happens when the integration tests pass locally but the workflow's service configuration differs? The workflow reads the same `.env.example` defaults the local stack uses, so a divergence is a bug in one place rather than two.
- What happens to a commit that is fine locally and breaks only in CI? That is the intended division of labour, not a defect — the local hook is explicitly not the authority.
- What happens if someone reintroduces the removed checks into the local hook? Nothing breaks, but the cost returns. The trade is recorded so it is a decision rather than a drift.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A workflow MUST run on every push and on every pull request.
- **FR-002**: The workflow MUST provision PostgreSQL and an S3-compatible object store equivalent to the local development stack, using the same configuration defaults.
- **FR-003**: The workflow MUST run lint, strict type checking, the full test suite including integration tests, and traceability coverage.
- **FR-004**: Each of those four checks MUST be a separately identifiable step, so a failure names which one failed.
- **FR-005**: The workflow MUST fail when any check fails.
- **FR-006**: The local pre-commit hook MUST NOT require a running container runtime.
- **FR-007**: The local pre-commit hook MUST retain every check that needs no external service — lint, formatting, and the non-integration tests.
- **FR-008**: Integration tests MUST be identifiable so they can be selected and deselected, and the marker MUST NOT interfere with the existing traceability marker.
- **FR-009**: A check removed from the local hook MUST run in the workflow. No check may be dropped from both.
- **FR-010**: The division of labour between the local hook and the workflow MUST be documented where a contributor will find it.

### Key Entities

- **Fast gate**: the checks that need no external service. Runs locally on every commit and again in the workflow.
- **Full gate**: every check, including those needing live services. Runs in the workflow, and locally on demand.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no containers running, a commit of a documentation change succeeds.
- **SC-002**: With no containers running, a commit that breaks lint or a non-integration test is still rejected.
- **SC-003**: A pushed branch triggers a workflow run that provisions both services and reports a result for each of the four checks.
- **SC-004**: A deliberately broken integration test causes the workflow to fail, and the failing test is named in its output.
- **SC-005**: Every check that the local hook stops running is present in the workflow — verifiable by comparing the two lists.

## Assumptions

- GitHub Actions is the CI provider. The repository is hosted on GitHub and its remote is reachable; no other provider is configured or considered.
- The workflow runs on `ubuntu-latest` with a Linux container runtime available, so the services run as job services rather than through Docker Compose.
- Traceability coverage in the workflow is authoritative. The local hook no longer runs it, because `make validate` runs the full suite by design and that is the very cost being moved.
- Requirements verified only by integration tests earn `implemented` on the strength of a workflow run, not a local one. This is a change in where verification is established, not a weakening of it.
- No deployment, publishing or release step is in scope. This workflow only checks.
