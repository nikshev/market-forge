---
id: REQ-WP-035
title: A feed going quiet is announced, and so is its coming back
type: work-package
prd_ref: "§32, §45 Phase 8"
prd_lines: "4752-4781, 6911"
phase: 8
status: specified
depends_on: [REQ-WP-008, REQ-WP-034]
tags: []
---

## Requirement

PRD §45's Phase 8 lists "alerting on data outages;" and §32 gives the states
that make the phrase mean something:

    Each feature family has health state:

    - GOOD;
    - DEGRADED;
    - STALE;
    - INVALID.

    Signal eligibility rules:

    - channel data must be GOOD;
    - price/bar must be GOOD;
    - optional confirmations may be degraded but decrease confidence;
    - LOB-dependent signal cannot use stale book;
    - DeFi contribution becomes neutral/unknown if delayed.

    Health metrics:

    - WS reconnect count;
    - sequence gap rate;
    - event latency p50/p95/p99;
    - stale seconds;
    - missing bars;
    - duplicate rate;
    - chain RPC lag;
    - subgraph indexing lag;
    - ClickHouse insert delay.

**Four states, not a boolean.** DEGRADED and STALE are different facts with
different consequences in the eligibility rules directly above them — a degraded
confirmation lowers confidence and a stale book disqualifies a signal outright.
Collapsing them into "unhealthy" would make the eligibility rules unimplementable
while looking like a simplification.

**An outage alert with no all-clear is worse than none.** Silence after a
failure notice is ambiguous: it reads as "still down" and as "nobody is
watching" equally well, and the reader has no way to tell. The recovery is the
half of the message that lets somebody stop worrying, and it is the half a
system reliably forgets, because a recovery feels like the absence of a problem
rather than an event.

**Alerting on state rather than on change floods.** A feed hovering at a
threshold produces an alert on every observation, and a channel that cries
constantly is one nobody reads — which loses the outage exactly as silence
would, but expensively. Announce transitions.

**An operational alert must never look like a trading signal.** They travel the
same wire to the same reader, who acts on one and investigates the other, and a
reader who confuses them at a glance does the wrong thing quickly.

## Acceptance

- A feed's health is one of the four PRD states, and DEGRADED, STALE and INVALID
  remain distinguishable from each other everywhere they are carried.
- An alert is raised on a change of state, not on each observation of a bad one.
- A return to GOOD is announced, naming what recovered and how long it was
  degraded.
- The same state observed twice in a row produces one alert, not two.
- An operational alert is distinguishable from a trading signal in the message
  itself, not only by which code path produced it.
- The thresholds that decide a state are arguments, not constants — PRD §13.11's
  rule about defaults applies, and §32 supplies metrics without values.
- Operational alerts use the same dispatcher, retry policy and audit as every
  other notification.
- Nothing about the existing signal or stop notifications changes.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

§33's metric list (`stale feed count`, `Telegram delivery failures`) and the
dashboards that read it are a separate Phase 8 deliverable. This requirement is
the alert, not the metrics export; the two are named apart in §45 and stay apart
here.

The health state itself has no producer yet: no connector is running, so nothing
observes a reconnect count or a gap rate. This carries and announces the state,
as [[REQ-WP-031]] carried a ratio nothing writes. What fills it belongs with the
ingestion path.
