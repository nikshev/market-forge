---
id: OUT-2026-09-12-implement-hypercore
step: implement
records: [REQ-WP-048]
commit: null
---

## What was done

`tools/record/hypercore_capture.py`, one fixture holding a metadata pass plus an
interleaved websocket recording, and `connectors/hypercore/normalize.py`.
43 tests, 27 of 28 mutants caught.

## The symbol table is the requirement

§18.25 gives "market symbol normalization" one line. On this venue it is where
the failures live, and all of them are quiet:

- **Three key shapes in `allMids`** — 235 bare, 380 `@`, 382 `#`. A key is not a
  symbol until something says which.
- **Delisted perps keep their index.** 56 of 234, the first at index 3, and the
  asset-context list is positional against the same universe. A table built from
  the still-listed assets is right for BTC, ETH and ATOM and wrong for every one
  after — pairing one asset's funding and open interest with another's name.
- **Spot pairs are sparse the other way**: 326 pairs, indices to 716. One venue,
  two index conventions, and the two mistakes are opposites. That is why this
  module has two lookups rather than one clever one.
- **The endpoints are not a snapshot of each other.** 55 `@N` keys matched no
  pair in metadata read seconds earlier. Refused, because the alternative is
  resolving them to a neighbour.
- **`#N` is refused outright.** Its values arrive in pairs summing to one, which
  is consistent with binary markets and is not evidence. 382 keys nobody can
  name, and a guess would attribute a real series to an instrument that does not
  exist. The observation is recorded as a test so the next person can take it
  further.

## What `side` means, measured

A trade carries `"B"` or `"A"` — the taker's direction, or the resting side it
hit. Interleaved with the best bid and offer over 143 recorded trades on one
connection: `"B"` executed at or above the ask **47 of 47**, `"A"` at or below
the bid **35 of 36**. The taker's side. The single exception arrived before the
quote update that had already moved the price, which is what an interleaved
recording looks like.

Same method as [[OUT-2026-09-11-implement-okx]]'s, and cleaner: OKX needed 158
messages to reach the same confidence.

Two smaller measured facts: 143 trades carried 143 distinct `tid`, so §18.25's
de-duplication has a key that is actually a key; and USDC is eight wei decimals
on HyperCore with `evm_extra_wei_decimals: -2`, so a HyperEVM amount differs by
a hundred — which §18.11.3's cross-layer comparison would read as an arbitrage.

## A flaw in how every sweep this session was run

The HyperCore sweep reported a mutant as surviving that, applied by hand,
failed three tests. The cause was not the mutant:

**Python's bytecode cache validates on `(mtime, size)`.** Two consecutive
mutants that produce files of *identical size* within the same second reuse the
first one's `.pyc`. The second mutant's run therefore executed the first
mutant's code — and reported its result.

Here that turned a caught mutant into a false survivor, which is the harmless
direction. It can equally turn a survivor into a false *caught*, which is not.

Every sweep this session was re-run with `PYTHONDONTWRITEBYTECODE=1`, and every
previously reported number is confirmed: Slipstream 23/0, Curve 34/1, Cryptoswap
32/8, Uniswap v4 25/0. Only the HyperCore reading was wrong, and it was wrong in
the direction that cost work rather than hid it.

**The deeper problem is that the sweep harness is not a project artifact.**
Mutation testing is this project's acceptance standard and its tooling has been
ad-hoc scratch scripts, re-typed for each requirement, so a flaw in one is a
flaw in all of them and a fix in one fixes nothing else. That wants a committed
tool, and is the next piece of work rather than part of this one.

## The one survivor

Deleting the empty-key guard. The fallthrough already refuses — an empty string
is not a perp — so the guard only improves the message. Kept for that, uncaught
for the same reason the early band guards in `curve.py` are.

## What is still open

- **§18.11.2's HyperEVM ingestion profile**: the standard EVM pipeline pointed
  at another chain.
- **§18.25's reconnect and snapshot recovery**, which belong with the socket.
- **§18.11.3's cross-layer features**, which the PRD itself calls "hypotheses
  only until validated OOS" and which need both halves first.
