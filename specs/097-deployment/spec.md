---
traces: [REQ-WP-056]
status: draft
---

# Feature Specification: The stack can be run by somebody who did not build it

**Feature Branch**: `wp-056-deployment`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-056 — Phase 8's deployment documentation and the observability stack.

## Context

The repository documents development. Nothing says what runs in front of a user,
what it needs, or what it does not do. [[REQ-WP-055]] left the same gap one level
in: the exposition is served and the dashboard defined, and nothing scrapes or
renders either.

**The documented profile is not PRD §6.2's.** That section names `clickhouse`,
which [[ADR-002]] dropped before any of it was built, and `redis`, which nothing
needs. A document repeating it would describe a system that does not exist —
worse than no document, because a reader would look for a service nobody deploys
and conclude the deployment is broken.

**Documentation rots in a way that looks exactly like documentation.** A command
renamed, a service removed, a variable spelled differently: each leaves prose
that is confident, plausible and wrong, and none of it fails anything.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The document cannot quietly go stale (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a command the document names, **When** checked, **Then** it is a real target.
2. **Given** a service the document names, **When** checked, **Then** it is in the compose file.
3. **Given** a service in the compose file, **When** checked, **Then** the document describes it.
4. **Given** a variable in the example, **When** checked, **Then** the document names it.

---

### User Story 2 - The exposition is scraped and rendered (Priority: P1)

**Acceptance Scenarios**:

1. **Given** the scrape configuration, **When** compared with the route, **Then** the paths match.
2. **Given** the committed dashboard, **When** compared with the definition, **Then** they agree.
3. **Given** the rendered dashboard, **When** inspected, **Then** unproduced metrics are text, not graphs.

---

### User Story 3 - The gaps are named (Priority: P2)

**Acceptance Scenarios**:

1. **Given** what §6.2 lists and this stack omits, **When** read, **Then** each carries the decision that removed it.
2. **Given** what the deployment does not cover, **When** read, **Then** it is stated.

### Edge Cases

- **Two tables of service names with opposite meanings.** A check reading both would assert that a removed service is in the compose file.
- **A credential in the example.** A name with an empty value, never a secret.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every command the document names MUST be a real target.
- **FR-002**: Every service it names MUST be in the compose file, and every running service MUST be described.
- **FR-003**: Every variable it names MUST be in the example, and every example variable MUST be documented.
- **FR-004**: The example MUST carry names with empty values for credentials.
- **FR-005**: The scrape path MUST be asserted against the route, not repeated.
- **FR-006**: The dashboard file MUST be generated and checked against the definition.
- **FR-007**: An unproduced metric MUST render as text, not as a graph.
- **FR-008**: The document MUST name what §6.2 lists and this stack omits, with the decision behind each.
- **FR-009**: The document MUST state what the deployment does not cover.
- **FR-010**: No test may start a container.

### Key Entities

- **Deployment document**: what runs, what it needs, what it does not do.
- **Generated dashboard**: the definition in the shape the tool reads.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every name in the document resolves against the repository.
- **SC-002**: The committed dashboard equals the rendered definition byte for byte.
- **SC-003**: Nine unproduced metrics render as text panels.
- **SC-004**: No test starts a container.

## Assumptions

- **Prometheus reaches the API on the host.** The API runs from the host in
  development; containerising it is a separate decision nobody has needed.
- **Grafana is anonymous.** A development stack holding no secrets and reachable
  from nowhere, rather than a password nobody rotates.

## Open Questions

- **Production images.** Nothing is containerised beyond the stateful services,
  and writing an image before there is somewhere to deploy it would be guessing
  at a base and a supervisor.
