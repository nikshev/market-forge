---
id: REQ-WP-036
title: A metric nobody writes is absent, not zero
type: work-package
prd_ref: "§33, §45 Phase 8"
prd_lines: "4783-4800, 6910"
phase: 8
status: planned
depends_on: [REQ-WP-008, REQ-WP-035]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "monitoring dashboards;" and §33 says what they read:

    ## Metrics

    Prometheus-compatible:

    - events/sec by connector;
    - reconnects;
    - book resets;
    - ingest latency;
    - feature compute latency;
    - channel compute latency;
    - signal count;
    - Telegram delivery failures;
    - DB insert latency;
    - queue depth;
    - stale feed count.

**A metric nobody writes must be absent from the exposition, not exported as
zero.** This is the same rule this codebase has applied to features, ratios and
health readings, arriving in the place where it does the most damage. A gauge
sitting at zero because nothing increments it is indistinguishable, on a
dashboard, from a healthy zero. Every alert built on it stays green forever, and
the failure it was meant to catch is now invisible *and* believed to be watched
— which is worse than having no dashboard, because a missing dashboard is
noticed.

Eleven metrics are listed and a handful have producers today. Exporting all
eleven so the dashboard "looks complete" would be exactly the failure above,
performed deliberately.

**Prometheus-compatible means the text exposition format**, which is a contract
with something outside this repository: a name, optional labels, a value, and a
`# TYPE` line. Getting it subtly wrong produces a scrape that fails silently or,
worse, one that parses into the wrong series.

**No clock.** A metric is a reading at an instant that the caller supplies, as
every other reading in this system is — otherwise a replay produces different
metrics from the run it replays.

## Acceptance

- A metric with no recorded observation does not appear in the exposition.
- A metric observed with the value zero does appear, and reads as zero.
- The exposition parses as Prometheus text format: one `# TYPE` line per metric,
  names and labels well-formed, values numeric.
- Labels distinguish series that share a name — a per-connector metric with two
  connectors is two series, not a sum.
- Counters only increase; a counter asked to decrease is refused rather than
  silently clamped.
- Telegram delivery failures and stale feed count are derived from the audit and
  the health assessments that already exist, not from a parallel counter a caller
  must remember to bump.
- Metrics that no part of this system produces are named as unimplemented in one
  place, rather than exported as zero or silently omitted from the list.
- No wall clock anywhere; every instant is an argument.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

This is the exposition, not the dashboards. §45 lists "monitoring dashboards"
as one deliverable and this delivers the half that belongs in this repository; a
Grafana definition describes a deployment that does not exist yet, and the
remaining half stays in `not_delivered` where it can be disagreed with.

The rule at the top has a name in this vault already — [[ADR-016]] made it about
alert blocks, and [[REQ-WP-031]] about a ratio. It is the same rule.
