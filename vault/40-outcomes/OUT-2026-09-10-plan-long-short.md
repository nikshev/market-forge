---
id: OUT-2026-09-10-plan-long-short
step: plan
records: [REQ-WP-031]
commit: null
---

## What was done

`specs/069-long-short/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/readings.md`, `quickstart.md`. [[REQ-WP-031]] moves to `planned`.

## What was decided

- **Positioning is its own module, not more functions in `state.py`.**
  `state.py` holds what every derivative reading shares — `state_at`,
  `require_fresh`, `z_score`. Positioning consumes that machinery. Keeping the
  split stops the shared floor growing a per-feature wing each time a feature
  lands, which is the shape `state.py` was already drifting toward.
- **`None` is the default and nothing fills it.** No sentinel, because `-1.0`
  and `NaN` are both floats, both survive arithmetic, and both eventually arrive
  somewhere as a number.
- **Two refusals, not one.** `None` means the venue is answering and published
  nothing; `NoStateAvailable` means there is no answer. A reading that collapsed
  them would make a silent venue and a dead connector look alike.
- **The quickstart tells the reader how to break it.** Both failure modes —
  absence defaulting to 1.0, and the history reading past the instant — leave a
  module that returns plausible numbers for every input. The only way to show
  the tests are load-bearing is to name the edit and the test that catches it.

## What is still open

- Nothing new. The two open items from [[OUT-2026-09-10-spec-long-short]] stand:
  nothing writes positioning yet, and the connector field mapping is deliberately
  undecided.
