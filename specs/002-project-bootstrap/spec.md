---
traces: [REQ-WP-001]
status: draft
---

# Feature Specification: Project Bootstrap

**Feature Branch**: `002-project-bootstrap`

**Created**: 2026-09-07

**Status**: Draft

**Input**: REQ-WP-001 — Tasks: create pyproject; setup `uv`; ruff; mypy; pytest; frontend scaffold; docker compose; Makefile. Done when: one command starts dev stack.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start the development stack with one command (Priority: P1)

A developer clones the repository, runs one command, and has the project's
backing services running locally: a PostgreSQL instance for transactional
metadata and an S3-compatible object store for the canonical data plane. They
can connect to both and confirm they answer.

**Why this priority**: This is the requirement's only stated acceptance
criterion. Nothing else in Phase 0 can be exercised against real services until
it holds, and every later work package assumes it.

**Independent Test**: From a clean checkout with no containers running, execute
the single documented command, then connect to each service and perform a
trivial operation — a `SELECT 1` against PostgreSQL and a bucket listing against
the object store. Delivers a working local environment on its own, with no
application code required.

**Acceptance Scenarios**:

1. **Given** a clean checkout with no containers running, **When** the developer runs the documented start command, **Then** PostgreSQL and the object store both reach a healthy state and accept connections.
2. **Given** the stack is already running, **When** the developer runs the start command again, **Then** it succeeds without error and does not duplicate or restart services unnecessarily.
3. **Given** the stack is running, **When** the developer runs the documented stop command, **Then** both services shut down and the data volumes persist for the next start.

---

### User Story 2 - Run the quality gate on a clean checkout (Priority: P2)

A developer runs the project's lint, type-check and test commands and gets a
green result on an untouched checkout, so that any later red result is
attributable to their own change rather than to the environment.

**Why this priority**: A baseline that is not green is worse than no baseline —
it teaches people to ignore the gate. This must hold before any product code is
written, but it does not depend on the services from Story 1.

**Independent Test**: On a clean checkout, run the lint, type-check and test
commands. All three pass with no findings and no skipped configuration.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the developer runs the lint command, **Then** it reports no findings for both style and formatting.
2. **Given** a clean checkout, **When** the developer runs the type-check command, **Then** it reports no errors under strict settings for the product source tree.
3. **Given** a clean checkout, **When** the developer runs the test command, **Then** the suite passes and its output is free of warnings.

---

### User Story 3 - Build the web application shell (Priority: P3)

A developer installs the frontend dependencies and produces a production build
of an empty application shell, confirming the frontend toolchain and its pinned
versions work before any interface is designed.

**Why this priority**: Listed in REQ-WP-001's tasks, but nothing depends on it
until the chart work in REQ-WP-009. Its value here is fixing the toolchain and
version choices early, cheaply, while they are still free to change.

**Independent Test**: Install dependencies and run the build. It produces
output artifacts and exits successfully, with no application behaviour to
verify beyond the shell rendering.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** the developer installs frontend dependencies and runs the build, **Then** the build completes and emits static artifacts.
2. **Given** the frontend dependencies are installed, **When** the developer runs the frontend type-check, **Then** it reports no errors.

---

### Edge Cases

- What happens when a required host port is already occupied by another process? The start must fail with a message naming the port and the service, not hang or silently bind elsewhere.
- What happens when the container runtime is not installed or not running? The start must fail with a message that says so, rather than a generic error from the orchestration tool.
- What happens when the stack is started twice concurrently? The second invocation must not corrupt the first's state.
- How does the system handle a developer on a machine whose architecture differs from the images' primary platform? Image selection must not silently fall back to emulation without saying so.
- What happens to data between stops and starts? Volumes persist by default; a separate, explicitly destructive command is required to discard them.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST provide a single documented command that starts the full local development stack.
- **FR-002**: The development stack MUST consist of PostgreSQL and an S3-compatible object store, and MUST NOT include any analytical database service (per ADR-002).
- **FR-003**: Each service MUST declare a health condition, and the start command MUST NOT report success until every service is healthy.
- **FR-004**: The start command MUST be idempotent — running it against an already-running stack succeeds and changes nothing.
- **FR-005**: The repository MUST provide a documented command to stop the stack that preserves data volumes, and a separate command to discard them.
- **FR-006**: Service credentials and ports MUST be configurable through an environment file, with a committed example carrying development-only defaults. Real credentials MUST NOT be committed.
- **FR-007**: The Python project MUST declare its dependencies and tooling configuration in a single project file, pinned to Python 3.12.
- **FR-008**: The repository MUST provide commands for linting, formatting checks, static type checking, and running tests, each usable independently.
- **FR-009**: Static type checking MUST run under strict settings over the product source tree.
- **FR-010**: The repository MUST contain a web application scaffold that builds successfully and type-checks, containing no charting library and no product interface.
- **FR-011**: The quality-gate commands MUST pass on a clean checkout before any product code exists.
- **FR-012**: Every command in FR-001, FR-005 and FR-008 MUST be discoverable from the repository's own documentation, not only from this specification.

### Key Entities

- **Development stack**: the set of backing services a developer runs locally. Comprises a transactional metadata store and an object store; each has a health condition, a host port, and a persistent volume.
- **Environment file**: the single place where service credentials, ports and connection settings are declared. Has a committed example form and an uncommitted local form.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a clean checkout on a machine with only the container runtime and the Python package manager installed, a developer reaches a running stack with one command and no manual steps.
- **SC-002**: The start command reports success only after every service answers a real request, verified by connecting to each and performing a trivial operation.
- **SC-003**: Lint, type-check and test commands all pass on a clean checkout with no findings, no errors, and no warnings in output.
- **SC-004**: Running the start command twice in succession produces the same end state as running it once.
- **SC-005**: Stopping and restarting the stack preserves data written between the two.
- **SC-006**: The frontend scaffold builds and type-checks with no errors.

## Assumptions

- A container runtime (Docker or a compatible replacement) is installed and running on the developer's machine. Installing it is out of scope.
- The object store is provided by a MinIO container rather than a local directory, per ADR-002: the target storage profile makes S3-compatible object storage the canonical data plane, and developing against a filesystem would reintroduce a local-versus-production divergence.
- No analytical database is provisioned. Research queries will run through DuckDB as a library over Parquet extracts when there is data to query; this is ADR-002's decision and is not revisited here.
- No application service is containerised in this feature. The API and workers run from the host during development. Phase 0's "services boot locally" is satisfied for backing services only; application services arrive with the code that needs them.
- The frontend scaffold uses the stack PRD §7 names — React, TypeScript and Vite — but excludes Lightweight Charts, which belongs to REQ-WP-009.
- Database schema and migrations are out of scope. This feature provisions an empty PostgreSQL instance; the domain schema arrives with REQ-WP-002.
- Continuous integration is out of scope. The commands defined here are what CI would later run, but no CI configuration is created.
