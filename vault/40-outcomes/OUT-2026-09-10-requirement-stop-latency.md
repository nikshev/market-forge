---
id: OUT-2026-09-10-requirement-stop-latency
step: requirement
records: [REQ-WP-033]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-033.md`, extracted from PRD §44A.27 and §45's
Phase 7A acceptance line. One of [[REQ-PHASE-7A]]'s two remaining deliverables.

## What was decided

- **The PRD supplies its own failing example**, so the requirement quotes it
  rather than inventing one: decision at `.100`, acknowledgement at `.260`,
  market touch at `.180`. The touch falls in the gap, and today's replay would
  evaluate it against a stop that did not exist yet.
- **The bias is not one-directional, and that is the argument for modelling it
  rather than reasoning about it.** An instantly-effective tighter stop
  sometimes exits earlier than reality would have and sometimes locks a profit
  reality would have given back. "It's conservative" is unavailable as an
  excuse in either direction.
- **Zero latency must be expressible and must not be the default.** A default of
  zero means every caller who did not think about it gets the optimistic case
  and a number that looks like a measurement. This is the "absent is not zero"
  rule pointed at a parameter rather than at a reading.
- **The report must name the latency it ran under.** Two reports produced under
  different latencies are not comparable, and nothing about their shape says so.
- **§44A.27's ordering rule is included** rather than split off: "never choose
  whichever ordering gives better PnL" is about the same gap, and a requirement
  that modelled latency while leaving the resulting ambiguity to be resolved by
  whatever reads better would have delivered the mechanism and lost the point.

## What is still open

- **Whether the latency is one number or three.** §44A.27 names decision,
  computation and network/exchange as separate contributions. Whether the replay
  models them separately or as a declared total is a spec question, and the
  answer bears on what a report can honestly attribute a difference to.
- **What "ambiguous" does to a comparison.** Marking an outcome ambiguous is
  only useful if the report cannot then average it away, and how that is
  enforced is not settled here.
