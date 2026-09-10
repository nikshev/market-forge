---
traces: [REQ-WP-036]
status: draft
---

# Feature Specification: A metric nobody writes is absent, not zero

**Feature Branch**: `wp-036-metrics`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-036 — part of Phase 8's monitoring deliverable.

## Context

PRD §33 lists eleven Prometheus-compatible metrics. A handful have producers in
this repository; most describe connectors and pipelines that do not run yet.

The whole requirement is what happens to the rest. **A gauge sitting at zero
because nothing increments it is indistinguishable, on a dashboard, from a
healthy zero.** Every alert built on it stays green forever, and the failure it
existed to catch becomes invisible *and* believed to be watched — a worse
position than having no dashboard at all, because a missing dashboard is
noticed and a green one is trusted.

The same rule has been applied here to alert blocks ([[ADR-016]]), to a
positioning ratio ([[REQ-WP-031]]) and to a feed's health ([[REQ-WP-035]]). This
is its most consequential appearance, because a monitoring system is precisely
the thing people stop checking once it looks fine.

Two smaller things have to be right. The exposition is a contract with something
outside this repository, so a subtly malformed one fails silently at scrape time
or parses into the wrong series. And no metric may read a clock: an instant is
an argument, or a replay produces different metrics from the run it replays.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Absence survives to the dashboard (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a metric nothing has observed, **When** the exposition is rendered, **Then** it does not appear.
2. **Given** a metric observed as zero, **When** the exposition is rendered, **Then** it appears and reads zero.
3. **Given** the list of metrics §33 names, **When** somebody asks what is exported, **Then** the unimplemented ones are named as unimplemented in one place.

---

### User Story 2 - The exposition is what a scraper expects (Priority: P1)

**Acceptance Scenarios**:

1. **Given** any exposition, **When** it is read, **Then** each metric carries one `# TYPE` line.
2. **Given** two connectors, **When** a per-connector metric is rendered, **Then** it is two labelled series, not a sum.
3. **Given** a label value containing a quote or a newline, **When** it is rendered, **Then** it is escaped rather than breaking the format.

---

### User Story 3 - The numbers come from what already happened (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a dispatcher audit with failures, **When** delivery failures are counted, **Then** the count comes from the audit.
2. **Given** health assessments, **When** the stale feed count is read, **Then** it comes from those assessments.
3. **Given** a counter, **When** it is asked to decrease, **Then** it is refused.

### Edge Cases

- **A counter observed as zero.** Present, and zero. The difference from absence is the point.
- **A metric with labels in one place and none in another.** Two series under one name, which Prometheus permits and a reader must be able to tell apart.
- **An empty registry.** An empty exposition, not a page of zeroes.
- **The same series observed twice.** The later value wins for a gauge; a counter accumulates.
- **A metric name that is not a valid Prometheus name.** Refused at registration, where it can be fixed, rather than at scrape time in production.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A metric with no observation MUST NOT appear in the exposition.
- **FR-002**: A metric observed as zero MUST appear.
- **FR-003**: The exposition MUST be valid Prometheus text format, including one `# TYPE` line per metric and escaped label values.
- **FR-004**: Series sharing a name MUST be distinguished by labels, never summed.
- **FR-005**: A counter MUST refuse to decrease.
- **FR-006**: Delivery failures MUST be derived from the dispatcher audit.
- **FR-007**: Stale feed count MUST be derived from health assessments.
- **FR-008**: §33 metrics with no producer MUST be named as unimplemented in one place.
- **FR-009**: No wall clock; every instant MUST be an argument.
- **FR-010**: An invalid metric name MUST be refused at registration.

### Key Entities

- **Metric**: a name, a type, and the series observed under it.
- **Exposition**: what a scraper reads, containing only what is known.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An unobserved metric is absent from the exposition and an observed zero is present.
- **SC-002**: The rendered text parses as Prometheus exposition, with types and escapes correct.
- **SC-003**: Two connectors produce two series under one name.
- **SC-004**: A decrement is refused.
- **SC-005**: The delivery-failure count matches the audit it was derived from.
- **SC-006**: The unimplemented list names every §33 metric this system does not produce.

## Assumptions

- **This is the exposition, not the dashboards.** A Grafana definition describes
  a deployment that does not exist; the other half of §45's deliverable stays in
  `not_delivered` where it can be disagreed with.
- **No scrape endpoint here.** Whether the text is served by the existing API or
  a separate process is a deployment question, and deployment is its own Phase 8
  deliverable.
- **No client library.** The exposition format is a few lines of text and a
  dependency would import a global registry, a clock and a process collector —
  three things this codebase has spent requirements removing.

## Open Questions

- **Whether the unimplemented list should fail a test when §33 gains a metric.**
  It would catch drift from the PRD, and the PRD is read-only, so the drift can
  only come from a re-extraction.
