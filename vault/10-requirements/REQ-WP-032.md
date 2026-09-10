---
id: REQ-WP-032
title: The stop path is shown as it was generated, not as it would look today
type: work-package
prd_ref: "§44A.33, §45 Phase 7A"
prd_lines: "6464-6500, 6887"
phase: 7A
status: draft
depends_on: [REQ-WP-020, REQ-WP-028]
tags: []
---

## Requirement

PRD §45's Phase 7A lists "stop-path chart;" and §44A.33 says what it must
display:

    Position page/chart must display:

    - entry;
    - initial stop;
    - hard catastrophic stop;
    - current adaptive stop;
    - historical stop path;
    - each stop proposal marker;
    - anchor used for each proposal;
    - rejected proposals;
    - current position phase;
    - open risk `R`;
    - locked profit `R`;
    - MFE/MAE;
    - trail aggressiveness;
    - reasons/vetoes;
    - data-health status.

    Clicking a stop update shows:

        Why moved:
        + confirmed higher low
        + channel remains UP
        + OFI recovered
        + MFE > activation threshold

        Why not tighter:
        - volatility floor
        - nearby HVN rotation zone
        - P(MAX) only moderate

    `AS-SEEN-THEN` mode must show the stop path exactly as generated
    live/replay, not recompute a prettier historical trail.

The last line is the requirement. Everything above it is a list of fields, and a
list of fields is satisfiable by drawing them. The line under it forbids the one
thing a chart naturally does: given a position and a price series, recomputing
the stop path is easier than storing it, produces a smoother trail, and is
wrong. A recomputed path uses anchors confirmed after the instant it draws them
at, and the result is a chart showing a stop that could not have been placed —
the visual form of the look-ahead Principle I forbids.

**Rejected proposals are a required field**, and are the second thing that makes
this more than a drawing. [[ADR-032]] already refuses to let a hold be `None`,
so six different holds stay distinguishable in the model. A view that drew only
the movements would collapse them again at the last step: a stop that held for
an hour because of a cooldown and one that held because no anchor was knowable
look identical as a flat line, and the difference is exactly what a reader
inspecting a stop decision needs.

## Acceptance

- The historical stop path is read from the stored proposals, never recomputed
  from price.
- In `AS_SEEN_THEN`, no proposal is drawn before the instant it was made, and no
  anchor is attributed to a proposal that could not have known it.
- Held and refused proposals are rendered as themselves, distinguishable from
  each other and from movements, not as absence.
- Every proposal carries its anchor and its reason codes to the view; a
  proposal whose reasons are dropped is a failure, not a plain marker.
- Entry, initial stop, hard stop and current adaptive stop are separate levels;
  an absent hard stop is absent, not equal to the initial stop.
- Open risk `R`, locked profit `R`, MFE and MAE come from the position and the
  path, and are refused rather than shown as zero when the path is empty.
- The existing chart views are unchanged.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

`AS_SEEN_THEN` is not a new concept here: [[REQ-WP-028]]'s `extrema.ts` already
filters extremum markers on knowledge, and this is the same mode over a
different series. Reusing the mode rather than inventing a second one is the
point — two implementations of "as seen then" would drift, and the drift would
be invisible, because both would draw lines.
