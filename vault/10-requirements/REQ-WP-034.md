---
id: REQ-WP-034
title: A stop update is announced with the risk it changed
type: work-package
prd_ref: "§44A.34, §45 Phase 7A"
prd_lines: "6504-6530, 6899"
phase: 7A
status: planned
depends_on: [REQ-WP-008, REQ-WP-020, REQ-WP-033]
tags: []
---

## Requirement

PRD §45's Phase 7A lists "Telegram stop-update notification;" and §44A.34 gives
the message:

    🛡 BTCUSDT LONG — STOP UPDATED

    Entry:          112,400
    Old stop:       111,180
    New stop:       112,060
    Price:          113,740

    Position phase: STRUCTURE_TRAIL
    Open risk:      1.00R -> 0.28R

    Anchor:
    confirmed higher low

    Reasons:
    + channel UP / quality 0.84
    + OFI recovery
    + volatility buffer satisfied

    [ OPEN POSITION CHART ]

    Do not notify for rejected micro-updates unless debug mode is enabled.

**Every line of that message is a transition, not a state.** Old stop against
new stop, open risk against the risk it replaced. A notification reporting only
where the stop now sits tells a reader what they can already see on the chart
and withholds the one thing they cannot: how much risk just came off. The
message is the difference, and a rendering that lost the "from" half would still
look complete.

**The old stop is the stop that was in force**, not the last one the policy
decided. [[REQ-WP-033]] separated those two, and a notification that announces a
move from a level the exchange never obeyed describes a change that did not
happen.

**The last line is a rate limit with a reason.** Stop policies hold far more
often than they move, and a channel that reports every held micro-adjustment
trains its reader to ignore it — at which point the alerts that matter are lost
in exactly the way silence would have lost them, but expensively.

## Acceptance

- The message states old stop and new stop, and open risk before and after, as a
  transition in both cases.
- The old stop is the stop that was in force when the move was decided.
- A held or refused proposal produces no notification unless debug mode is on.
- With debug mode on, a held proposal is announced as a hold, not as an update:
  the two are never rendered alike.
- The anchor and the reasons travel into the message; a reason the renderer does
  not recognise is shown, not dropped.
- A block with no source is absent rather than rendered with a dash ([[ADR-016]]).
- The existing signal alert is unchanged, and both kinds go out through the same
  dispatcher, gate and audit.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

The PRD's phrase "rejected micro-updates" admits two readings — rejections that
were micro, or rejections and micro-updates. The stricter reading is the safe
one and is the one to take: a stop update is announced when the stop moved, and
everything else is debug. That reading is stated where it is implemented, so a
future reader can disagree with it rather than discover it.
