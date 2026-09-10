---
id: OUT-2026-09-10-plan-derivatives-panes
step: plan
records: [REQ-WP-030]
commit: null
---

## What was done

`specs/068-derivatives-panes/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/check.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-030]] moves to `planned`.

## What was decided

- **The check parses the TypeScript source from the Python suite.** Unglamorous,
  and the only place the two real lists touch: a vitest check would need the
  feature names in TypeScript, which is a copy that agrees with itself forever.
- **The parser raises rather than returning nothing.** Found by the sweep:
  deleting the "nothing parsed" guard changed no result, because nothing ever
  handed the parser a source it could not read. The guard was real protection
  with no evidence behind it, and now two tests supply exactly those sources.
- **Which feature per pane.** Where a family offers several, the one chosen is
  the one a reader reads for that pane's question: the level for open interest,
  the z-score for funding, the basis in bps, the imbalance for liquidations.

## What is still open

- **Nothing writes derivative features into the feature table.** Named in the
  spec and not depended on.
