---
id: OUT-2026-10-11-implement-second-spot-venue
step: implement
records: [REQ-WP-098]
commit: null
---

## What was done

Implemented [[REQ-WP-098]] (spec 150) as far as the repository goes; status `tested` until the deployed run.

- `context/sources.py`: the one list `SERIES`, the OKX spot pairs mapped to their pairs' perpetuals, `book_symbols_for`
  and `market_type_of`; the OKX collector therefore also polls `ETH-USDT-SWAP` and `SOL-USDT-SWAP`.
- `context/book.py`: a book's market type and size rule are asked of the instrument (`BASE-QUOTE` spot, sizes in base
  units; `BASE-QUOTE-SWAP`, contracts converted, refused without a contract value); each stored minute carries its own
  instrument's market type.
- `pipeline/context_main.py`: book symbols are the venue's own series, apart from the perpetuals it polls.
- `crossvenue/deployment.py`: OKX spot BTC/ETH/SOL join the spot groups, so each has two venues.
- Compose: three ingest services (`ingest-okx-spot-{btc,eth,sol}`), with defaults so a local `.env` need not change.
- Mutation sweeps: three files, 34 mutations, survivors reasoned.

## Evidence

**RED first**: 13 of the new tests failed before the implementation (the series list, the book kind/size rule, the
spot groups, the settings). A recorded OKX **spot** `books` frame (`ws5_okx_books_spot.json`) is a fixture: its sizes
are the base coin's (1.019 BTC at the first ask), where the recorded swap's are contracts.

**GREEN**: the context, crossvenue and pipeline suites (533 tests) pass; lint and type check clean.

## What was decided / found along the way

- A test that fed recorded frames through the task found that **a minute closes in event time**: recorded frames carry
  the venue's own times, so the fake clock has to start at the latest of them. The Binance tests never saw it because
  Binance's depth frames carry no timestamp and take the receipt's.
- The deployment tests that count things (ingest services: five, now eight) are the tests that notice a service was
  added; they were updated with the reason beside the number.

## What is still open

- Deployment: the three ingests, the OKX collector, then the worker; SC-001 and SC-002 are measurements of that.
