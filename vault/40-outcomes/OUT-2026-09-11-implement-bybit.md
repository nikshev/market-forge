---
id: OUT-2026-09-11-implement-bybit
step: implement
records: [REQ-WP-043]
commit: null
---

## What was done

`tools/record/bybit_capture.py`, six recorded fixture files from the live public
venue, and `connectors/bybit/normalize.py`. 14 tests, 12 of 12 mutants caught,
every gate green.

## A rung I tried to skip

I wrote no spec, reasoning that [[REQ-WP-003]]'s established shape and
[[ADR-004]]'s fixture rule left nothing open. `make validate` refused the
requirement under R1, and it was right twice: the rung is not mine to waive, and
the reasoning was false. There **were** decisions — the taker-side mapping, one
entry point for two message types, `u` over `seq`, refusing rather than
skipping. I had taken them while building instead of before, which is a
different thing from there being none.

`specs/081-bybit-connector/spec.md` records them, says in its own Context that
it was written after the fact, and files them under "Decisions taken while
building" rather than folding them in as foresight.

## What the recorded traffic said that the documentation did not

**Gap detection uses `u`, not `seq`.** The orderbook page's prose says "monitor
sequential `seq` values; discontinuities indicate missed updates requiring
resubscription". Its own field table calls `seq` a *cross* sequence, for
comparing different depth levels. The two disagree, and forty consecutive
recorded messages settle it:

    u   deltas: {1}
    seq deltas: min 34, max 289, across 33 distinct values

A gap detector written from the prose would resubscribe constantly on a
perfectly healthy stream. This is [[ADR-004]]'s whole argument arriving as a
number, and it is why the fixture rule exists rather than being a preference.

**A linear trade carries `L`, a price-change direction, that spot does not.**
Noticed because PRD §5.2 says "Bybit linear perps" and a first probe had gone to
spot — which would have produced a working connector for a market this
project's universe does not include.

## The difference worth the most care

Binance sends `m`, whether the *buyer* was the maker, and the aggressor is
derived. Bybit sends `S`, which its documentation calls the taker side directly.
One canonical field, two conventions.

The mutation sweep inverted both mappings and both were caught — but only
because the tests assert the mapping against the raw field rather than against a
fixed expectation. A test that had asserted "the first trade is a sell" would
have passed for the inverted connector on a recording that happened to start
with a sell.

## What the sweep found

Eleven mutants died against the first test set. One survived: **swapping bids
and asks.** It reconstructs cleanly, passes every sequencing test, and inverts
the spread — an order book with the best bid above the best ask is
arithmetically fine and economically impossible, and every microstructure figure
above it would be wrong in a direction nobody could trace back to a connector.
There is a test for it now.

## What is still open

- **OKX**, the same requirement for a different venue, deliberately separate.
- **Funding and open interest** arrive on other Bybit channels and belong with
  the derivatives path.
- **The session layer.** This is normalisation; reconnect and ping lifecycle are
  [[REQ-WP-003]]'s `session.py` for Binance, and Bybit's 20-second ping is
  currently only in the capture tool.
