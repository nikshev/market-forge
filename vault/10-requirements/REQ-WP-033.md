---
id: REQ-WP-033
title: A stop update is not effective until it has been acknowledged
type: work-package
prd_ref: "§44A.27, §45 Phase 7A"
prd_lines: "6304-6314, 6898"
phase: 7A
status: specified
depends_on: [REQ-WP-020]
tags: []
---

## Requirement

PRD §45's Phase 7A lists as an acceptance line:

    - paper/shadow replay models stop-update activation latency;

and §44A.27 states the rule and gives its own example:

    Stop updates are effective only after modeled decision + computation +
    network/exchange latency.

    Example:

        signal computed at 10:15:00.100
        stop modification ack at 10:15:00.260

        market touch at 10:15:00.180

    The new stop was not yet active.

A replay that applies a decided stop from the instant it was decided reports a
position protected by a level that did not exist yet. In the PRD's own example
the touch at `.180` falls in the gap: the position is still holding the old stop
and the replay says it was holding the new one.

The bias does not run one way, which is exactly why it must be modelled rather
than argued about. An instantly-effective tighter stop sometimes exits earlier
than reality would have, and sometimes locks a profit reality would have given
back. Both are wrong, and a report built on them compares policies against a
market that acknowledged instructions before they were sent.

The same section states what must not be done about the ambiguity that follows:

    If one OHLC bar contains both:

        new stop trigger
        and
        profit target

    and ordering cannot be known, mark ambiguous or choose conservative ordering
    according to predeclared policy.

    Never choose whichever ordering gives better PnL.

## Acceptance

- A stop decided at `t` is not effective before `t + latency`; a trigger against
  it in that interval is evaluated against the stop that was actually active.
- The latency is a declared, modelled quantity, named as modelled, not a
  constant buried in the replay.
- A latency of zero is expressible and is not the default: the default states
  a non-zero cost, because a replay whose default is instantaneous reports the
  optimistic case whenever nobody chose.
- The comparison report says which latency it was produced under; two reports
  produced under different latencies are not comparable and must not silently
  look it.
- Where a point cannot resolve the ordering of a trigger and a target, the
  outcome is marked ambiguous or resolved by a predeclared conservative rule —
  never by whichever ordering pays better.
- Existing replay results are unchanged when the latency is zero.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

This is the same shape as [[REQ-WP-026]]'s staleness rule and
[[REQ-WP-031]]'s freshness-on-the-reading: a value that exists is treated as a
value that was available. Here the gap is between deciding and being obeyed.
