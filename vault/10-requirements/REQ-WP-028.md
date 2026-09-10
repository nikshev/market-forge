---
id: REQ-WP-028
title: Extrema reach the chart, and a confirmation never appears before it was known
type: work-package
prd_ref: "§45 Phase 1A, §13A.1, §27.2, §29.B"
prd_lines: "6720-6737"
phase: 1
status: draft
depends_on: [REQ-WP-019, REQ-WP-009, REQ-STORE-002, REQ-API-001]
tags: []
---

## Requirement

PRD §45's Phase 1A lists "chart markers for candidate vs confirmed extrema" and
states an acceptance criterion for them:

    - no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;

The detector exists ([[REQ-WP-019]]) and produces both shapes: an
`ExtremumCandidate` with its `observed_at_ns`, and a `ConfirmedExtremum` carrying
`extremum_time_ns`, `known_at_ns` and the lag between them — "the two timestamps
and the lag between them are the whole point", in its own words.

**They reach nothing.** No table holds them, no repository serves them, no
endpoint returns them, and the chart draws channels and a volume profile. The
last entry in [[REQ-PHASE-1A]]'s `not_delivered` is therefore four layers deep
rather than a drawing change.

**Why the criterion is the requirement.** An extremum happens at one instant and
becomes knowable at a later one. A marker placed at `extremum_time_ns` on a chart
showing the past *as seen then* claims the system knew about a turn before it
did — which is the repaint PRD §13A.1 exists to forbid, drawn on a screen and
believed. A candidate drawn like a confirmation makes the same claim more
quietly.

## Acceptance

- confirmed extrema and candidates are stored on the canonical plane and read
  back with every field, timestamps included;
- both repositories answer alike;
- an endpoint serves them for a window, and a caller can ask as of an instant;
- **in `AS-SEEN-THEN` mode at instant `t`, a confirmed extremum appears only if
  `known_at_ns <= t`** — never at its own `extremum_time_ns` alone;
- a candidate is drawn distinguishably from a confirmation, and neither is drawn
  as the other;
- a candidate that was later confirmed is not shown twice as though two turns
  happened;
- appending later bars does not change what a past instant shows.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

The other six of Phase 1A's deliverables are built; this is the last, and it is
the one that puts the phase's own correctness property in front of a reader.

**Scope is the path, not a second detector.** Nothing here re-derives an
extremum: the detector's output is stored, served and drawn. Where a value is
computed is [[REQ-WP-019]]'s business and stays there.

**`CURRENT REFIT` is out of scope for the filter.** PRD §27.5's other mode
recomputes over visible history and is explicitly the place where repaint-like
differences are meant to show. The criterion above names `AS-SEEN-THEN` and so
does this requirement.
