---
id: SPEC-066-extremum-markers
requirement: REQ-WP-028
speckit_path: specs/066-extremum-markers/spec.md
status: draft
---

## Summary

The detector produces a candidate while a swing forms and a confirmation when
the reversal crosses its threshold. The confirmation carries when the turn
happened, when it became knowable, and the lag between them — "the two
timestamps and the lag between them are the whole point", in its own docstring.

None of it reaches a table, a repository, an endpoint or the chart. Phase 1A's
last deliverable is four layers deep.

PRD §45 states what must be true once it arrives: **no confirmed extremum may
appear earlier than `known_at` in `AS-SEEN-THEN` mode.** That is the feature. A
marker at the turn's own instant, on a chart showing the past as it was seen
then, claims the system knew about the turn before it did — the repaint §13A.1
forbids, drawn where it will be believed. A candidate drawn like a confirmation
makes the same claim more quietly.

Two filters apply and they are separate: a window decides what is in view, and
knowledge decides what may be shown at all. Collapsing them would make a
correctness rule look like a range query.

## Links

- Requirement: [[REQ-WP-028]]
- The phase it closes: [[REQ-PHASE-1A]]
- The detector whose output it carries: [[REQ-WP-019]]
- The chart and its two modes: [[REQ-WP-009]]
