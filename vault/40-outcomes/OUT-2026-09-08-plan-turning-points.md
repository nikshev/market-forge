---
id: OUT-2026-09-08-plan-turning-points
step: plan
records: [REQ-WP-019, REQ-NRT-A, REQ-NRT-B, REQ-NRT-C, REQ-NRT-D, REQ-NRT-E]
commit: null
---

## What was done

Five modules under `src/channelflow/extrema/`, four test files, 17 tasks in
five phases.

## What was decided

- **The five non-repainting tests share one file.** PRD §13A.28 states them as
  a single mandated suite and they are read together; five files would let one
  quietly disappear without the absence being obvious.
- **`causality.py` is separate from `detector.py`.** [[ADR-022]]'s guard is a
  rule about the production path, not a property of one detector — §13A.30's
  local-polynomial and Kalman baselines will use the same guard.
- **The threshold is stored with the confirmation, not recomputed.**
  Recomputing it later, for a report or a chart, is exactly how a
  point-in-time value silently becomes a hindsight one.
- **`ConfirmedExtremum` refuses `known_at < extremum_time` at construction.**
  Test C then tests a property the type enforces rather than a convention the
  code is trusted to follow.

## What was rejected

- **Inferring centredness by inspection.** [[ADR-022]] has the argument: the
  four common forms of the defect look nothing alike, and a checker catching
  three would give false confidence about the fourth.
- **A fixed appendix in Test A.** A fixed series could be the one a broken
  detector happens to survive. It appends random bars.

## What is still open

- Nothing from this step. What the feature does not cover is in the spec's
  assumptions and [[ADR-023]].

## R5 fired during this step, correctly

Setting the five `REQ-NRT-*` notes to `planned` alongside REQ-WP-019 produced
five R5 violations: a `hard_gated` constraint may not hold any status past
`specified` without a linked test. `/sdd-plan`'s own step 4 says exactly this —
write the failing test first and go straight to `tested`, skipping `planned`.

They stay at `specified` until their tests exist. This is the first time R5 has
fired on real work rather than in its own unit tests, and it fired for the
right reason.
