---
id: OUT-2026-09-11-implement-okx
step: implement
records: [REQ-WP-044]
commit: null
---

## What was done

`tools/record/okx_capture.py`, five recorded fixture files, and
`connectors/okx/normalize.py`. 14 tests, **13 of 13 mutants caught on the first
sweep** — the first module this session where nothing survived.

A spec was written **before** the code this time. [[REQ-WP-043]]'s was not and
the validator caught it; the difference is visible in the artefacts, not just in
the order: SC-002's five-to-one threshold and the edge case about a trade
arriving before its delta were decided in the spec rather than discovered while
a test failed.

## The finding this connector exists for

**OKX quotes trade size in contracts.** `BTC-USDT-SWAP` carries `ctVal = 0.01
BTC`. Read like Binance's or Bybit's quantity, every volume on this instrument
would be a hundredfold too large — and the failure has no symptom, because the
numbers stay positive, ordered and plausible. The cross-venue comparison this
phase exists for would read that hundredfold difference as a finding.

A probe could not have caught it. `sz: 0.17` is $134 as contracts and $13,400 as
base units, and both are ordinary single trades. Only the instrument data
settles it, which is why the contract value is an argument read from the venue
rather than a constant.

Two venues agreeing taught nothing. The third disagreeing is where the canonical
model earned its name.

## What `side` means, measured rather than looked up

OKX's field table does not render through any fetchable documentation page. So
it was measured, from 158 interleaved recorded messages replayed against a
maintained book:

    buy  -> at/above ask:  25   at/below bid:   1
    sell -> at/above ask:   0   at/below bid:  91

That is the taker's side: a taker buying lifts the ask, a taker selling hits the
bid. The single exception is a trade that arrived before the delta which had
already moved the price — what an interleaved recording looks like, not a
counter-example.

The finding is a test over committed fixtures rather than a sentence, because a
test fails when the venue changes and prose does not. Its threshold is
overwhelming rather than absolute for the same reason the exception exists.

## What the venue does better than its neighbours

OKX's book states its own chain: every `prevSeqId` is the previous message's
`seqId`, and a snapshot's is `-1`. Binance sends a range and Bybit a single
incrementing id; here a gap is detectable without remembering anything.

## A process failure of mine, recorded

I merged [[REQ-WP-043]] to `main` **before its CI finished**, with a commit
message that said "CI green" when I did not yet know. It was green, so nothing
broke — but the message asserted a fact I had not checked, which is the same
error as any other unverified claim and worse for being about verification. The
`gh` account had also silently switched again mid-session, which is what made me
look.

## What is still open

- **Funding, open interest and mark price** arrive on other channels for both
  new venues.
- **The session layer** — reconnect and ping lifecycle — exists for Binance and
  not for Bybit or OKX; their ping intervals currently live only in the capture
  tools.
- **Symbol mapping across venues**, which is Phase 5's next deliverable and the
  thing these two connectors were built for.
