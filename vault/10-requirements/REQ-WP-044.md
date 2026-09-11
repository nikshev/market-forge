---
id: REQ-WP-044
title: OKX swaps arrive as the same canonical events, in base units
type: work-package
prd_ref: "§5.2, §45 Phase 5, §35.6"
prd_lines: "315-319, 6826, 4897-4906"
phase: 5
status: draft
depends_on: [REQ-WP-043]
tags: []
---

## Requirement

PRD §45's Phase 5 lists `OKX;` and §5.2 names the product:

    - Top 20–50 liquid Binance USDⓈ-M perpetuals;
    - Bybit linear perps;
    - OKX swaps.

The PRD's own reference list names the documentation:

    - OKX API documentation:
      https://www.okx.com/docs-v5/

**This venue quotes size in contracts, and that is the whole requirement.**
Binance and Bybit send a quantity in the base asset. OKX sends `sz` as a number
of contracts, and `BTC-USDT-SWAP` carries `ctVal = 0.01 BTC` per contract —
verified from the venue's own instruments endpoint and corroborated by its
documentation ("for FUTURES/SWAP/OPTION, `sz` refers to the number of
contracts").

A connector that took `sz` as a base quantity would report volumes **one
hundred times too large** on this instrument. Every volume-derived feature —
volume profile, CVD, order-flow imbalance — would be wrong by that factor, and
nothing downstream would show a symptom: the numbers stay positive, ordered and
plausible. The cross-venue work this phase exists for would then compare a
Binance figure against an OKX figure a hundredfold larger and call the
difference a finding.

**The contract value is per instrument and must be read, not assumed.** It
differs by instrument and can change; a constant compiled into the connector
would be right until the day it silently was not.

**What `side` means must be established, not guessed.** Binance sends whether
the buyer was the maker, Bybit sends the taker's side, and OKX's documentation
does not render the field table through any fetchable page. It is therefore
determined from recorded traffic — a taker's buy executes at the ask — and the
determination is recorded as a test over committed fixtures rather than as a
sentence somebody has to trust.

## Acceptance

- A recorded OKX trade normalises to the canonical `TradeEvent` with quantity in
  the **base asset**, converted using the instrument's own contract value.
- The contract value comes from the venue's instrument data, not from a constant.
- An instrument whose contract value is unknown is refused rather than assumed to
  be one.
- The aggressor side is established from recorded traffic and asserted by a test
  over the committed fixtures.
- A recorded book snapshot and its deltas reconstruct with no gap, and the best
  bid sits below the best ask.
- Event time is the venue's own timestamp; ingestion time is ours.
- Every fixture is captured from the live public venue by a committed tool, and
  no test opens a socket.
- Nothing about the Binance or Bybit connectors changes.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Scope is public market data: trades and the order book, as [[REQ-WP-043]]'s was.
Funding, open interest and mark price arrive on other channels and belong with
the derivatives path.

The contract-size problem is the reason this requirement is not simply
"[[REQ-WP-043]] again for a different venue". Two venues agreeing on a
convention taught nothing; the third disagreeing is where the canonical model
earns its name.
