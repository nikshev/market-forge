---
id: REQ-WP-048
title: HyperCore normalizes into the same CLOB primitives, and refuses what it cannot name
type: work-package
prd_ref: "§18.11, §18.25, §18.27, §45 Phase 4"
prd_lines: "3089-3146, 3600-3605, 3654-3655, 6793-6794"
phase: 4
status: implemented
depends_on: [REQ-WP-044]
tags: []
---

## Requirement

PRD §18.11 splits Hyperliquid in two:

    Hyperliquid must be split into **HyperCore market data** and **HyperEVM
    chain data**.

and §18.11.1 says where the market-data half lands:

    Normalized output maps into the same CEX/CLOB primitives used for
    Binance/Bybit/OKX:

        market.trade
        market.book_snapshot
        market.bbo
        derivatives.funding
        derivatives.open_interest
        market.reference_price

    Therefore HyperCore participates in order-flow, depth imbalance, OFI and
    derivatives analytics—not the AMM liquidity-map path.

§18.25 names four things the adapter must get right: reconnect/snapshot
recovery, book freshness, trade de-duplication, and **market symbol
normalization**.

**The symbol problem is the substance here**, and it is larger than the phrase
suggests. Measured against the live public API on 2026-09-12:

- **`allMids` has 997 keys in three shapes**: 235 bare names, 380 beginning `@`
  and 382 beginning `#`. A key is not a symbol until something says which shape
  it is.
- **`meta.universe` holds 234 perps of which 56 are delisted**, at indices 3,
  20, 22, 30, 32, 33 and onward — and **a delisted asset keeps its index**. A
  mapping built by enumerating the assets that are still listed is correct for
  BTC, ETH and ATOM and wrong for everything after index 3, by a drift that
  grows. This is the failure shape this phase keeps meeting: positive, ordered,
  believable.
- **`spotMeta.universe` is sparse in the opposite direction**: 326 pairs with
  indices running to 716, so the pair at position `i` is not pair `i`. One
  venue, two index conventions, opposite mistakes.
- **55 `@N` keys in `allMids` resolve against no pair in `spotMeta`**, read
  seconds apart. The two endpoints are not a consistent snapshot of each other.
- **A spot pair's `name` is sometimes its own index.** `@0` is `PURR/USDC`;
  `@107` is named `"@107"`.
- **Ten builder-deployed perp dexes exist besides the main one**, with assets
  named `xyz:AAPL`, `flx:GOLD`, `vntl:OPENAI`. None of them appears in
  `allMids` under that name.
- **What `#N` denotes is not established.** Its values arrive in pairs summing
  to one, which is consistent with binary markets and is not evidence.

**A token's HyperCore size and its HyperEVM amount are not the same number.**
`spotMeta.tokens` carries `evmContract.evm_extra_wei_decimals`, which is `-2`
for USDC. §18.11.3's cross-layer features compare a HyperCore mid against a
HyperEVM DEX price, and a factor of a hundred in between would read as an
arbitrage.

**`l2Book.levels` is positional.** Bids and asks arrive as `[[…],[…]]` with
nothing labelling which is which, so reading them in the wrong order produces a
book that is crossed rather than empty — and a crossed book is a signal, which
makes the error worse than a missing one.

## Acceptance

- A key from `allMids` resolves to a named instrument, or is refused. Nothing
  is guessed, and `#N` is refused for as long as nobody can say what it is.
- A perp asset index resolves through the venue's own ordering including
  delisted assets, and a mapping that skips them is shown to disagree.
- A spot pair index resolves by its `index` field rather than its position, and
  the two are shown to differ on live data.
- An `@N` key with no pair in the accompanying `spotMeta` is refused, not
  dropped and not resolved to its neighbour.
- An `l2Book` message normalizes to a book snapshot whose bids are below its
  asks, with the level ordering asserted rather than assumed.
- A trade normalizes into the same `TradeEvent` the other three venues produce,
  with the aggressor side established from the venue's own data rather than
  assumed.
- An asset context normalizes into `DerivativesState` with funding, open
  interest and a reference price, and an absent field stays absent rather than
  becoming zero.
- A token's EVM decimal offset is carried, and a conversion that ignores it is
  shown to differ.
- The fixtures are captures of real public responses at a named time, taken by
  a committed tool, and no test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**No credentials anywhere.** Hyperliquid's `info` endpoint answers unsigned POST
requests, which is why this venue was reachable at all under the constraint that
no KYC is involved.

**Scope is the market-data half.** §18.11.2's HyperEVM ingestion profile is the
standard EVM pipeline pointed at another chain, and §18.11.3's cross-layer
features are explicitly *"hypotheses only until validated OOS"* — both are
separate work, and the second cannot start until the first two exist.

**Reconnect and snapshot recovery are §18.25's and are not here.** They belong
with the socket, and this module touches no socket — the shape [[REQ-WP-003]]
established. Book freshness and trade de-duplication are normalization
properties and are in scope.
