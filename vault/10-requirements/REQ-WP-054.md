---
id: REQ-WP-054
title: The DEX depth curve reaches the screen with its refusals intact
type: work-package
prd_ref: "§27.2, §28, §18.12.3, §45 Phase 4"
prd_lines: "4406-4421, 4461-4500, 3195-3215, 6793-6794"
phase: 4
status: implemented
depends_on: [REQ-WP-053, REQ-WP-009, REQ-API-001]
tags: []
---

## Requirement

PRD §27.2 lists **"DEX liquidity bands"** among the main chart's toggle layers.
The web app has no DEX overlay, and until [[REQ-WP-053]] there was nothing for
one to read: the depth curves existed only in memory, inside whichever process
computed them.

Now they are a canonical table, so the remaining work is the path from it to the
screen — a repository read, a §28-shaped endpoint, a typed client call and a
layer the chart can toggle.

**The thing most likely to be lost on that path is [[ADR-036]]'s refusal.** A
depth quote whose `reachable` is false describes *exhausting the known
liquidity*, not reaching the target: the band was never reached and the notional
is what ran out, not what it costs. Every stage between the table and the pixel
has an opportunity to drop that flag, and each one turns "this pool is too thin
to move 100 bps" into "100 bps costs this much here" — which is a cheaper-looking
market than exists, drawn in the same ink as a real one.

So `reachable` travels as far as the drawing, and a band that was not reached is
drawn as not reached rather than omitted. **Omitting it would be the same lie by
absence:** a chart with no 100 bps band reads as a chart nobody asked about 100
bps.

**The overlay reads as of the chart's instant.** §27.5 already distinguishes
what was known then from what is known now, and a depth layer that fetched the
latest curve onto a historical chart would be the look-ahead Principle I forbids,
arriving through the one door nobody guards.

**A failed load is not an empty pool.** FR-016 of [[REQ-WP-009]] says a failed
load must never be drawn as though it were data, and an absent overlay and an
empty one are indistinguishable on a chart unless the difference is drawn.

## Acceptance

- A §28-shaped endpoint serves depth bands for a pool as of an instant, and
  refuses a request without one rather than defaulting to the latest.
- Prices and notionals cross the wire as exact strings, as bars already do.
- `reachable` and `reached_bps` survive from the table to the client, asserted at
  each boundary rather than only at the end.
- The overlay distinguishes a reached band from an unreached one visually, and a
  test asserts the two produce different output.
- An unreached band is present and marked, never omitted.
- A failed or absent load renders as a stated absence, not as an empty overlay.
- The overlay's instant is the chart's, and a test shows a later band is excluded.
- No test opens a socket, and the web tests run in the existing CI steps.

## Notes

Human territory. Never machine-rewritten.

**§27.3's "DEX active liquidity" pane is not here.** It is a lower pane rather
than a chart overlay, reads a different primitive, and bundling them would make
both harder to review.

**This is the first overlay that can refuse.** Every existing layer draws a
series that either exists or does not; a depth band can exist *and* decline to
answer, which is a state the overlay vocabulary in `overlays.ts` has never had to
carry.
