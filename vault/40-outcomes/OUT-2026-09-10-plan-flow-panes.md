---
id: OUT-2026-09-10-plan-flow-panes
step: plan
records: [REQ-WP-027]
commit: null
---

## What was done

`specs/065-flow-panes/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/panes.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-027]] moves to `planned`.

## What was decided

- **Three panes, from the PRD's list of nine.** The rest belong to Phases 3 and
  4; offering an empty pane and calling it a feature puts unfinished work in
  front of a reader as though it were finished.
- **Gap and zero are implemented and tested as a pair.** Either alone is
  satisfiable by an implementation that gets the other wrong.
- **Three empty-ish states, not one blank.** The main chart already refuses one
  blank for everything, and a new pane showing one would have undone that
  quietly.
- **The decision is a pure function.** Mirrors `series.ts`, which exists for the
  same reason and says so in its own header: jsdom cannot lay out a chart, so a
  component test can never see a line.

## What is still open

- **How a gap looks is a consequence, not a decision.** The component draws a
  polyline over whatever points come back, so a gap is a break in the line. A
  reviewer may prefer it marked, and nothing here forecloses that.
