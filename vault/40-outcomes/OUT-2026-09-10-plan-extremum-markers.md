---
id: OUT-2026-09-10-plan-extremum-markers
step: plan
records: [REQ-WP-028]
commit: null
---

## What was done

`specs/066-extremum-markers/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/extrema.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-028]] moves to `planned`.

## What was decided

- **The event time is knowledge, not the turn.** `known_at_ns` for a
  confirmation, `observed_at_ns` for a candidate. The plane's point-in-time read
  then makes PRD §45's Phase 1A acceptance a property of the storage rather than
  something every reader has to remember. Keying on the turn's own instant would
  have made every such read a repaint.
- **The turn's instant travels beside it**, because that is where the marker
  goes once the row may be returned at all. `read_*` sorts by it, since that is
  what a chart draws.
- **Two lists, not one with a flag.** A caller telling a candidate from a
  confirmation by inspecting a field is a caller that will forget, and the
  failure is silent: a candidate drawn as a confirmation looks exactly like one.
- **Optional numbers are strings, empty for absent.** Fifth place in this
  repository the distinction has had to be drawn.
- **Only `AS-SEEN-THEN` filters.** PRD §27.5 makes the other mode the place
  where repaint-like differences are meant to show; filtering there would hide
  the difference while looking like extra safety.

## What is still open

- **The in-memory repository applies the rule by hand**, because it has no plane
  to enforce it. The conformance suite is what keeps the two answers equal, and
  it is the only thing that does.
