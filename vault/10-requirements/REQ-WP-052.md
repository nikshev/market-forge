---
id: REQ-WP-052
title: Both Hyperliquid layers plug into the machinery that already exists
type: work-package
prd_ref: "§18.11.2, §18.25, §45 Phase 4"
prd_lines: "3121-3134, 3600-3605, 6793-6794"
phase: 4
status: implemented
depends_on: [REQ-WP-014, REQ-WP-048, REQ-WP-051]
tags: []
---

## Requirement

PRD §18.11 splits Hyperliquid in two. [[REQ-WP-048]] normalized the market-data
half; this is what remains of both.

**§18.11.2: HyperEVM enters the standard EVM pipeline**, with its block identity
tracked separately. [[REQ-WP-014]] built that pipeline against Ethereum, and its
chain properties are defaults on `FinalityPolicy`. Measured on 2026-09-12 across
three independent RPC endpoints:

    chain       block time   `safe` lag   `finalized` lag
    -------------------------------------------------------
    Ethereum      ~12s        33 blocks     65 blocks
    HyperEVM        1s         0 blocks      0 blocks

HyperEVM's `latest`, `safe` and `finalized` are **the same block** — HyperBFT
finalises within the block, and all three endpoints agree. Pointing Ethereum's
defaults at it means waiting sixty-four seconds to call final what the chain
finalised a second ago: 768 seconds to finality against 1, from the same code,
decided entirely by which numbers it was handed.

**The reverse is what makes this a requirement rather than a tuning exercise.**
Carry HyperEVM's depths onto Ethereum and the pipeline calls a block finalised
that can still reorg. Same numbers, and one direction is latency while the other
is wrong data — which is why a chain with no measured profile must be refused
rather than defaulted.

**§18.25: reconnect, snapshot recovery and book freshness for HyperCore.**
Measured: the venue closes an idle connection at 60.6 seconds **with no close
frame**, the same shape as Bybit, and `{"method":"ping"}` every twenty seconds
keeps it — a fourth venue and a fourth payload convention, after Binance's
server-initiated ping, Bybit's `{"op":"ping"}` and OKX's bare `ping`.

Because the venue announces nothing, a consumer holding the last book it
received cannot tell a quiet market from a dead socket. **An old book is not a
wrong book** — it is a right book about a moment that has passed, and every
check it passes it passes honestly.

## Acceptance

- HyperEVM has a measured chain profile: identity, block time, finality depths
  and more than one endpoint.
- A chain with no profile is refused, not given a neighbour's depths.
- A test shows the two profiles' time-to-finality differ by orders of magnitude
  from the same policy machinery.
- HyperCore has a session policy carrying its measured idle timeout, its
  keepalive payload and the fact that it announces nothing, and drives the shared
  session ([[REQ-WP-051]]) unchanged.
- A test shows the four venues' ping payloads are four different things.
- A book older than a caller-supplied bound is refused, and the bound has no
  default.
- A book age is signed, so a venue clock ahead of ours is visible rather than
  clamped.
- No test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**Ethereum's `safe_depth` is left alone and flagged.** At 12 it calls a block
safe some twenty blocks before Ethereum's own `safe` tag does — a heuristic that
predates the tag existing. Changing it changes what every existing consumer of
this pipeline sees, which is a decision with its own evidence to gather rather
than a detail of this one.

**Freshness lives with the venue that needed it.** It is generic enough to move
when a second venue wants it; putting it in a shared place today would be
designing for a caller that does not exist.
