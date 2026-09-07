---
id: REQ-PHASE-1A
title: Extremum baseline
type: phase
prd_ref: "Phase 1A — Extremum baseline"
prd_lines: "6720-6737"
phase: 1A
status: draft
depends_on: ["REQ-PHASE-1"]
tags: []
---

## Requirement

Deliverables:

- directional-change confirmed highs/lows;
- causal local-polynomial slope/curvature;
- extremum candidate lifecycle;
- immutable `extremum_time` vs `known_at` semantics;
- chart markers for candidate vs confirmed extrema;
- replay/non-repaint tests;
- no ML required.

Acceptance:

- no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;
- appending future bars does not mutate finalized candidates/confirmed extrema;
- confirmation lag and prominence are reported.

## Acceptance

- no confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode;
- appending future bars does not mutate finalized candidates/confirmed extrema;
- confirmation lag and prominence are reported.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
