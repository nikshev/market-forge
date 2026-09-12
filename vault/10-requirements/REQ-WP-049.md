---
id: REQ-WP-049
title: Bybit and OKX report funding and open interest in comparable units
type: work-package
prd_ref: "§17, §35.6, §45 Phase 5"
prd_lines: "2560-2576, 4897-4903, 6821-6832"
phase: 5
status: implemented
depends_on: [REQ-WP-043, REQ-WP-044]
tags: []
---

## Requirement

PRD §45's Phase 5 lists Bybit, OKX and **funding dispersion**. The first two
landed as public market data ([[REQ-WP-043]], [[REQ-WP-044]]); neither reports
derivatives state, so there is no cross-venue funding series to disperse.

Binance already produces `DerivativesState` from REST, and HyperCore from its
asset contexts. This is the other two venues, and the point is not that the data
exists — it is that **the two venues disagree about units and about names in
ways that produce confident wrong findings.** Both measured against the live
public endpoints on 2026-09-12:

**Open interest is in contracts on OKX and in base units on Bybit.** OKX's
`/public/open-interest` returns `oi`, `oiCcy` and `oiUsd`; `oi` is contracts and
`BTC-USDT-SWAP` carries `ctVal = 0.01 BTC`. Measured:

    OKX oi     = 2,745,005 contracts
    OKX oiCcy  =    27,450 BTC
    Bybit      =    53,250 BTC

Read `oi` as base and OKX appears to hold **51.5 times** Bybit's open interest.
Read correctly it holds **0.52 times** — about half, which is the actual market
structure. The first number is positive, ordered and believable, and would be
reported as a finding. It is the same failure [[REQ-WP-044]] met in trade size,
now in a field nothing else cross-checks.

**The two venues name the same instant differently.** OKX's funding response
carries `fundingTime` *and* `nextFundingTime`; Bybit's ticker carries
`nextFundingTime`. Measured at the same moment:

    OKX   fundingTime     = 2026-09-12 16:00
    OKX   nextFundingTime = 2026-09-13 00:00
    Bybit nextFundingTime = 2026-09-12 16:00

**`OKX.fundingTime` is `Bybit.nextFundingTime`**, exactly. A connector that maps
each venue's `nextFundingTime` into the same field puts OKX eight hours late,
and a dispersion computed across a settlement boundary compares one venue's
settled rate against another's forthcoming one.

**One call against three.** Bybit returns funding, open interest, mark and index
from a single ticker endpoint. OKX needs three, and they carry three different
timestamps — so an OKX state is assembled from readings taken moments apart, and
how far apart is a fact worth carrying rather than discarding.

## Acceptance

- Bybit and OKX each normalize into the same `DerivativesState` the other venues
  produce, from recorded public responses.
- Open interest is reported in base units for both venues, and a test shows that
  reading OKX's contract count as base gives a figure tens of times wrong.
- The contract value comes from the venue's own instrument data, not a constant.
- The funding settlement instant is the same field for both venues, and a test
  shows the two venues' like-named fields are eight hours apart.
- An absent field stays absent: a venue that publishes no funding is not a
  venue whose funding is zero.
- An OKX state records how far apart its three readings were taken, and a state
  assembled from readings further apart than a configured bound is refused.
- Time parsing is asserted for both venues (§35.6), and a malformed or missing
  field is refused rather than defaulted.
- The fixtures are recorded public responses captured by a committed tool, and
  no test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**No credentials.** Every endpoint here is public: Bybit's `/v5/market/tickers`
and OKX's `/api/v5/public/*` answer unsigned.

**Funding dispersion itself is not here.** It is a cross-venue feature and wants
its own requirement; this is what makes it possible, and Phase 5's line about it
stays until it exists.

**The shared session layer is not here either.** Phase 5's acceptance asks that
each connector implement the shared canonical interface and pass the §35.6
contract tests, and today only Binance has a session. That is a separate piece of
work about lifecycle — reconnect, keepalive, rate limits — and bundling it with
units and field names would make both harder to review.
