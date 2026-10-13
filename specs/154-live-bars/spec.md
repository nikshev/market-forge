---
traces: [REQ-WP-102]
status: draft
---

# Feature Specification: A live chart

**Input**: [[REQ-WP-102]] -- owner's direction 2026-10-13. Builds on [[REQ-WP-066]], [[REQ-WP-068]], [[REQ-WP-042]], [[REQ-API-001]].

## Context

1. The 1m chart is up to fifteen minutes behind because the ingest commits fifteen bars at a time (`FLUSH_EVERY_BARS`); measured
   on 2026-10-12 as a last bar 861 s old.
2. The ingest already holds what the chart lacks: the bars it has built and not yet committed, and the bar it is building.
3. The stack already has the pieces: Redpanda and a Kafka-protocol transport with a JSON `Record` ([[REQ-WP-042]]), and an API
   WebSocket with subscriptions and a hub ([[REQ-API-001]]) that nothing publishes into.
4. The chart (lightweight-charts) can update the last candle in place; the page redraws everything on each REST reload, and
   the lower panes align to the chart by bar index, so a bar the chart has and a pane does not is a misalignment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The 1m chart is current (P1)

**Independent Test**: publish a forming bar for the current minute; the subscribed socket receives it, and the candle on the page changes without the chart being redrawn.

**Acceptance Scenarios**:

1. **Given** a subscriber to `bars` at `1m`, **When** the ingest publishes a forming bar, **Then** the subscriber receives it within a second.
2. **Given** a new subscriber, **Then** it first receives the cached bars of the last thirty minutes, then updates.
3. **Given** a final bar for a minute, **When** a forming bar for the same minute arrives late, **Then** the final one stays.

### User Story 2 - The page says what it is showing (P1)

**Acceptance Scenarios**:

1. **Given** the socket is open and bars arrive, **Then** the page says **live**; when it is closed or silent, **delayed**.
2. **Given** the socket drops, **Then** it is reopened with backoff and the periodic reload keeps running meanwhile.

### User Story 3 - The panes stay aligned (P2)

**Acceptance Scenarios**:

1. **Given** live bars after the last stored one, **Then** every pane's time axis has them, and the Volume pane draws their volume.

### Edge Cases

- Broker down at ingest start: the ingest runs, counting failures. Broker down at API start: no live feed, the page says delayed.
- Two ingests of one series (none today): the later forming bar wins by ingest time, and a final bar always wins.
- A reload of stored bars that now includes a minute the live feed also has: the stored bar supersedes.
