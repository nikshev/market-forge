---
id: REQ-WP-031
title: Long/short positioning is ingested, and its absence stays visible
type: work-package
prd_ref: "§16, §45 Phase 3"
prd_lines: "1778, 6767"
phase: 3
status: draft
depends_on: [REQ-WP-013, REQ-WP-026]
tags: []
---

## Requirement

PRD §45's Phase 3 lists "optional long/short stats;" and PRD §16's derivatives
feature list names what they are for:

    - long/short squeeze context where available.

Three words carry the requirement. **Squeeze context** is not the ratio: a
crowded book is a condition, and a number without a sense of how unusual it is
says nothing about crowding. **Where available** is the other half: not every
venue publishes positioning, and a market that does not publish it is not a
balanced market.

`DerivativesState` carries funding, open interest and basis, and nothing about
who is positioned which way. It is the last entry in [[REQ-PHASE-3]]'s
`not_delivered`.

## Acceptance

- a venue's long/short account ratio and top-trader ratio are carried on
  derivatives state, each optional;
- a ratio nobody published reads as absent, never as balanced — a ratio of 1.0
  is a real reading and means the opposite of an unknown one;
- the crowding reading is relative to the instrument's own recent positioning,
  not to a constant: a ratio of 2.0 is ordinary on one instrument and extreme on
  another;
- a reading refuses rather than guessing when there is too little history to say
  what is unusual;
- the features are registered like every other, with their null policy stated;
- a stale positioning reading is refused, as [[REQ-WP-026]] refuses a stale
  funding one — the same REST polling, the same failure;
- nothing that exists changes.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

**"Optional" describes the venue, not the rigour.** The PRD calls the stats
optional because a venue may not publish them. It does not follow that a feature
built on them may be sloppy about saying so — the opposite: a field that is
sometimes absent is exactly the field where an absent value silently becoming a
neutral one does the most damage, because nothing downstream will ever see a
gap.

**The squeeze reading is a z-score, and it refuses.** [[ADR-026]] settled that
for funding and open interest: zero is the most meaningful value a z-score can
take, and a feature that says "exactly average" whenever it has nothing to say
reads as a calm market to everything downstream. Positioning gets the same
treatment through the same shared function rather than a second one.
