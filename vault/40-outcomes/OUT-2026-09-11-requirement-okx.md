---
id: OUT-2026-09-11-requirement-okx
step: requirement
records: [REQ-WP-044]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-044.md`, from PRD §5.2 and §45's Phase 5, read
against the OKX v5 documentation and a probe of the live public stream.

## The finding that is the requirement

**OKX quotes trade size in contracts.** `BTC-USDT-SWAP` carries `ctVal = 0.01
BTC`, read from the venue's own instruments endpoint and corroborated by its
documentation: "for FUTURES/SWAP/OPTION, `sz` refers to the number of
contracts".

Binance and Bybit both send a base-asset quantity. Taking `sz` the same way
would report volumes **a hundredfold too large**, and nothing downstream would
notice: the numbers stay positive, ordered and plausible. The cross-venue
comparison this phase exists for would then read a hundredfold difference as a
finding.

A probe could not have caught it either. `sz: 0.17` on BTC-USDT-SWAP is 0.0017
BTC ≈ $134 if contracts and 0.17 BTC ≈ $13,400 if base units — both perfectly
ordinary single trades. Only the instrument data settles it, which is why the
requirement says the contract value must be read rather than assumed.

## What is deliberately unresolved

**What `side` means.** Binance sends whether the buyer was the maker; Bybit
sends the taker's side; OKX's field table does not render through any fetchable
documentation page. Rather than guess, the requirement says it is determined
from recorded traffic — a taker's buy executes at the ask — and that the
determination is asserted by a test over committed fixtures.

That is a stronger record than a sentence in a document: a test fails when the
venue changes, and a sentence does not.

## What is still open

- **Funding, open interest and mark price** arrive on other channels.
- **The session layer**, as with Bybit.
