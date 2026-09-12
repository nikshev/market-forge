---
id: REQ-WP-055
title: The metrics are served, and the dashboard names what nobody produces
type: work-package
prd_ref: "§33, §45 Phase 8"
prd_lines: "4783-4800, 6910"
phase: 8
status: implemented
depends_on: [REQ-WP-036, REQ-API-001]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "monitoring dashboards". [[REQ-WP-036]] built the
Prometheus-compatible exposition §33 asks for; nothing serves it over HTTP and
nothing draws it.

**Serving it is small. Drawing it is where the trap is**, and [[REQ-WP-036]]
already named the trap: of §33's eleven metrics, **nine have no producer** and
are recorded in `UNIMPLEMENTED` with a reason each —

    events/sec by connector    no connector runs; nothing counts an event
    reconnects                 a health reading carries it, but no session
                               reports one yet
    book resets                the book is reconstructed in tests only
    ingest latency             there is no ingestion path to time
    feature compute latency    features are computed on demand, not on a pipeline
    channel compute latency    the same
    signal count               the signal machine has no runner
    DB insert latency          writes go through the lakehouse plane, which
                               nothing times
    queue depth                there is no queue; ADR-018 made delivery
                               synchronous

A dashboard with eleven panels would draw nine of them empty, and **an empty
panel is indistinguishable from a healthy quiet system.** That is exactly what
[[REQ-WP-036]] exists to prevent, one level up: it refused to export those
metrics as zero *and* refused to drop them from the list, because the first
makes a dashboard lie and the second makes the gap invisible.

So the dashboard draws what exists and **states** what does not, from the same
`unimplemented_reasons()` mapping the code carries. A panel that says "no
connector runs; nothing counts an event" is worth more than a flat line at zero
and worth more than a missing panel.

**A dashboard is only true while the names match.** A panel querying a metric
nobody writes draws an empty panel; a metric renamed in the code leaves the
panel querying a name that no longer exists, and both look identical on screen.
So the definition is checked against the registry by a test rather than by
somebody opening it.

## Acceptance

- The exposition is served over HTTP with the content type Prometheus expects,
  and a scrape of a registry that has observed nothing returns an empty body
  rather than an error.
- Every metric a dashboard panel queries is one the registry can emit, asserted
  mechanically.
- Every metric in `unimplemented_reasons()` appears in the dashboard as a stated
  absence carrying its reason, and none of them appears as a queried panel.
- The two lists together cover §33's metrics, so a metric can be neither
  silently dropped nor silently duplicated.
- Adding a producer for an unimplemented metric fails the dashboard test until
  the dashboard is updated, and a test demonstrates that direction.
- No test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**Standing Prometheus and Grafana up is not here.** Wiring a scraper and a
renderer into the stack is deployment work and belongs with Phase 8's deployment
documentation, which is the next item. This requirement is the two halves that
must be right before either is worth running: something to scrape, and a
definition that cannot quietly go stale.

**The dashboard is a definition, not a rendering.** The same division
`volumeProfile.ts` has lived with since [[REQ-WP-012]] and `dexDepth.ts` since
[[REQ-WP-054]]: the decision about what to show is tested, and the drawing is
the tool's problem.
