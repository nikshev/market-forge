---
traces: [REQ-WP-055]
status: draft
---

# Feature Specification: The metrics are served, and the dashboard names what nobody produces

**Feature Branch**: `wp-055-metrics-serving`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-055 — Phase 8's monitoring dashboards.

## Context

[[REQ-WP-036]] built the Prometheus-compatible exposition §33 asks for. Nothing
serves it and nothing draws it.

Serving it is small. Drawing it is where the trap is, and [[REQ-WP-036]] already
named it: **nine of §33's eleven metrics have no producer**, each recorded with a
reason. A dashboard with eleven panels draws nine of them empty, and an empty
panel is indistinguishable from a healthy quiet system — a flat line at the
bottom reads as "nothing is going wrong", which is precisely what nobody knows.

That is the same failure [[REQ-WP-036]] refused one level down: it would not
export those metrics as zero, because that makes a dashboard lie, and would not
drop them from the list, because that makes the gap invisible.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Something to scrape (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a process that has measured nothing, **When** scraped, **Then** the body is empty.
2. **Given** an observed metric, **When** scraped, **Then** it appears with its type.
3. **Given** a registered metric nothing observed, **When** scraped, **Then** it is absent.
4. **Given** the response, **When** its content type is read, **Then** it names the exposition version.

---

### User Story 2 - A dashboard that cannot go stale quietly (Priority: P1)

**Acceptance Scenarios**:

1. **Given** every panel, **When** checked against the registry, **Then** each queries a metric something can emit.
2. **Given** a metric nobody registers, **When** observed, **Then** it is refused.
3. **Given** the unproduced metrics, **When** the dashboard is built, **Then** each appears as a stated absence with its reason.
4. **Given** a producer appearing, **When** the absences are derived, **Then** that metric leaves the list.

### Edge Cases

- **A metric drawn and stated.** Neither list may contain the other's entries.
- **A renderer reading only panels.** Absences travel in the document.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The exposition MUST be served over HTTP with the exposition-format content type.
- **FR-002**: An empty exposition MUST be served as an empty body, not an error or a placeholder.
- **FR-003**: The route MUST be outside the versioned read API.
- **FR-004**: Every panel MUST query a metric the registry can emit.
- **FR-005**: Every unproduced metric MUST appear as a stated absence carrying its reason.
- **FR-006**: No unproduced metric MAY appear as a panel.
- **FR-007**: Absences MUST be derived from the code, not transcribed.
- **FR-008**: Panels and absences together MUST cover §33's eleven.
- **FR-009**: Absences MUST travel in the rendered document.

### Key Entities

- **Panel**: something drawn, and what to take from it.
- **Absence**: something §33 asks for that nothing produces, and why.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two panels and nine absences, summing to eleven.
- **SC-002**: A scrape of an unmeasured process returns an empty body.
- **SC-003**: Removing a metric from the unimplemented list removes its absence.
- **SC-004**: No test opens a socket.

## Assumptions

- **Standing Prometheus and Grafana up is deployment work**, and belongs with
  Phase 8's deployment documentation. This is the two halves that must be right
  before either is worth running.
- **The dashboard is a definition, not a rendering**, as `volumeProfile.ts` and
  `dexDepth.ts` are.

## Open Questions

- **Whether an absence should carry a link to what would implement it.** Today
  the reason names the gap; it does not name the work.
