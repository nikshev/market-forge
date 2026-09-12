---
id: OUT-2026-09-12-implement-hyperliquid-layers
step: implement
records: [REQ-WP-052]
commit: null
---

## What was done

`chain/profiles.py`, HyperCore's session policy, book freshness on the HyperCore
normalizer, and three mutation specifications extended. 20 new tests, and the
full sweep now stands at 207 caught and 10 survived.

## The same pipeline, two chains, 768 seconds apart

Measured across three independent RPC endpoints, which all agreed:

    chain       block time   `safe` lag   `finalized` lag
    -------------------------------------------------------
    Ethereum      ~12s        33 blocks     65 blocks
    HyperEVM        1s         0 blocks      0 blocks

HyperEVM's `latest`, `safe` and `finalized` are **the same block**. HyperBFT
finalises within the block, so [[REQ-WP-014]]'s Ethereum-shaped defaults would
make this pipeline wait sixty-four seconds to call final what the chain finalised
a second ago — 768 seconds to finality against one, from the same code.

**The reverse is what made this a requirement rather than a tuning exercise.**
Carry HyperEVM's depths onto Ethereum and the pipeline calls a block final that
can still reorg. The same numbers: one direction is latency, the other is wrong
data. So a chain with no measured profile is refused rather than given a
neighbour's.

The test that carries the argument is one line: five confirmations is
`FINALIZED` on HyperEVM and `HEAD_CONFIRMED` on Ethereum. Nothing about the
number says which chain it belongs to.

## A finding left deliberately unacted on

**Ethereum's `safe_depth` of 12 calls a block safe some twenty blocks before
Ethereum's own `safe` tag does.** Measured: the tag lagged the head by 33.

The depth is a heuristic that predates the tag existing, and it is not wrong so
much as differently calibrated. Changing it changes what every existing consumer
of this pipeline sees, which is a decision with its own evidence to gather.
Recorded in the profile's docstring and in the specification's open questions,
and left alone.

## A fourth venue, a fourth ping

HyperCore closes an idle connection at **60.6 seconds with no close frame** —
the same shape as Bybit, measured the same way. And it wants `{"method":"ping"}`,
which is neither Bybit's `{"op":"ping"}` nor OKX's bare `ping` nor Binance's
server-initiated exchange.

Four venues, four conventions, and nothing about a venue's name predicts which.
The two that share a timeout and a silence convention still disagree about the
payload — the one field that decides whether the connection survives at all — so
there is a test asserting exactly that, because copying Bybit's policy would have
been right about everything else.

[[REQ-WP-051]] paid off here: the fourth venue is nine lines of data and no code.

## An old book is not a wrong book

Because the venue announces nothing when it gives up, a consumer holding the
last book it received cannot tell a quiet market from a dead socket. So §18.25's
"book freshness" is a refusal rather than a metric: a book past the caller's
bound is refused, and the bound has no default because a depth curve tolerates
more than a quote.

The age is signed. A venue clock ahead of ours is a fact about the pair of
clocks, and clamping it to zero would turn a skew problem into a book that is
eternally fresh.

## The harness, again

Two findings on this branch, both from the checks built in [[REQ-INFRA-004]]:

- **An ambiguous pattern.** Adding HyperCore's policy made
  `announces_close=False,` appear twice, so Bybit's mutation could have landed on
  either. Under the old scripts it would have silently mutated the first.
- **A survivor with no recorded reason**, which was mine: the `empty key`
  equivalent mutant had been explained in an outcome note and never written into
  the specification where the harness could check it.

## What is still open

- **Whether Ethereum's depths should follow the chain's own tags**, above.
- **Protocol-specific pool events on HyperEVM.** §18.11.2 lists them; the
  decoder registry from [[REQ-WP-014]] takes them without changes, and no DEX on
  that chain has been registered yet.
- **HyperCore↔HyperEVM transfer events**, which §18.11.2 wants "where they matter
  for asset-flow context" and §18.11.3 calls hypotheses until validated
  out-of-sample.
