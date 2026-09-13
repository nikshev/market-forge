---
traces: [REQ-WP-064]
status: draft
---

# Feature Specification: The API and the web app become images that start

**Feature Branch**: `wp-064-production-images`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-064 — PRD §6.2's `api` and `web` services.

## Context

REQ-WP-056 containerised the stateful half and documented it. Nothing else was
containerised, and the reason was worse than an absent Dockerfile: **nothing in
this project could be started as a process.** `create_app` takes an already-built
repository, `LakehouseRepository` takes a `Catalog`, and the only place a catalog
was opened was a test fixture pointing at a temporary directory.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The API starts from configuration (Priority: P1)

**Acceptance**: an image started with a catalog URI and a warehouse serves
`/readyz` with `ready: true`.

### User Story 2 - A misconfigured process refuses (Priority: P1)

**Acceptance**: a missing or blank required variable stops startup and names the
variable. There is no local-directory default.

### User Story 3 - Readiness means the store answered (Priority: P1)

**Acceptance**: with the catalog unreachable the endpoint returns 503 and the
cause; when it returns, 200.

### User Story 4 - The web app serves its own deep links (Priority: P2)

**Acceptance**: `/chart/binance/BTCUSDT` returns the application, and `/api/`
reaches the API service.

### Edge Cases

- An editable install links to the build stage's tree, which the runtime stage
  does not copy: the image builds and cannot import its own package.
- The catalog URI names a driver: `psycopg`, not `psycopg2`.
- §32's feed health must not answer a container probe.
- `worker` and `ingest-binance` do not exist as code.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `settings_from_env` reads two required variables and refuses a
  missing or blank one, naming all of them.
- **FR-002**: Storage options are read under pyiceberg's property names; a blank
  one is absent.
- **FR-003**: The catalog is opened through REQ-WP-041's one factory.
- **FR-004**: `/readyz` asks the catalog and answers 503 when it does not.
- **FR-005**: An app with no store says so rather than claiming one answered.
- **FR-006**: The API image installs the project `--no-editable` from the
  lockfile and runs as a non-root user.
- **FR-007**: Compose declares `api` and `web` and no service for a process this
  repository does not have.
- **FR-008**: No credential is literal in a compose file or an image; `.env` is
  excluded from the build context.
- **FR-009**: CI builds both images, starts the API against the live stack and
  probes it, and checks the refusal.

### Key Entities

- **Settings** — catalog URI, warehouse, storage options.
- **Readiness / Probe** — the answer and what was asked.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Both images build and the API serves `/readyz` in CI.
- **SC-002**: Stopping PostgreSQL turns `/readyz` to 503; starting it returns
  200.
- **SC-003**: An unconfigured image exits naming `CHANNELFLOW_CATALOG_URI`.
- **SC-004**: Mutating the required set, the blank check, the probe's verdict or
  the status code is caught by a test.

## Assumptions

- The web app calls the same origin it loaded from; nginx forwards `/api`.

## Open Questions

- Load generation against this deployment is Phase 8's remaining entry.
