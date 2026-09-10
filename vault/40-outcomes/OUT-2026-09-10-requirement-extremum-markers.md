---
id: OUT-2026-09-10-requirement-extremum-markers
step: requirement
records: [REQ-WP-028]
commit: null
---

## What was done

[[REQ-WP-028]] extracted from PRD §45's Phase 1A — its last unbuilt deliverable
and the acceptance criterion that governs it.

## What was decided

- **The PRD wrote the correctness rule, so the requirement is built around it.**
  "No confirmed extremum can appear earlier than `known_at` in `AS-SEEN-THEN`
  mode" is not a display preference: an extremum happens at one instant and
  becomes knowable at a later one, and a marker at the first claims the system
  knew about a turn before it did. That is the repaint §13A.1 forbids, drawn on
  a screen and believed.
- **The item is four layers, not a drawing change.** The detector produces both
  shapes and they reach nothing — no table, no repository, no endpoint. Calling
  this "frontend" undersells it, and the note says so rather than letting the
  size be discovered halfway.
- **A candidate drawn like a confirmation makes the same false claim, quietly.**
  Both are on the chart and they must not look alike.
- **`CURRENT REFIT` is out of scope for the filter.** PRD §27.5's other mode
  recomputes over visible history and is explicitly where repaint-like
  differences are meant to show. The criterion names `AS-SEEN-THEN`.

## What is still open

- **How the two markers differ visually is not fixed here.** Shape, colour or
  fill are all honest; what is required is that they are told apart.
- **Whether a confirmed extremum should replace its own candidate on the chart**
  is decided in the acceptance — not shown twice — but *how* is the plan's.
