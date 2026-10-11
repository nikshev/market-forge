---
id: OUT-2026-10-11-implement-book-subscription
step: implement
records: [REQ-WP-095]
commit: null
---

## What was done

Implemented [[REQ-WP-095]] (spec 147) as far as the repository goes. Status is `tested`: the panes enabled on the
running stack and the host load with the books running (SC-004 to SC-006) are measurements of the deployment.

- **`MinuteBook`** (`context/minute_book.py`): the existing `BookService` and `OFITracker`, finalised per minute in
  event time from the book **before** the message that closes the minute; 1 Hz sampling; a silent minute closed by the
  clock with a count of zero; a reconnect or a sequence gap breaks the flow baseline.
- **`book_minutes` table** and the **quotes** the same minute implies, in one sink.
- **The streams** (`context/book.py`): Binance spot `depth10@1000ms`, Bybit linear `orderbook.50`, OKX `books`; the
  frames recorded 2026-10-11; OKX contracts converted to base units; a lost sequence closes the connection.
- **`StreamTask`** gained a tick (so a quiet stream still closes its minutes) and a reconnect callback (so a new
  connection does not inherit the old book).
- **The worker pass** writes `ofi_1m` and `depth_imbalance_10`, in the same single commit as the other families, from
  the series' OWN market's book.
- The two registrations say what they now are (sampled once a second; no number for a book of fewer than ten levels).
- **Mutation sweeps**: five files, ~70 mutations, every survivor killed or reasoned.

## Evidence

**RED first.** The tests were written and run before any module existed:

    ERROR tests/unit/context/test_minute_book.py
    ERROR tests/unit/tables/test_book_minutes.py
    ERROR tests/unit/features/test_book_values.py
    3 errors during collection        (and the book-stream and pass tests, which import the same modules)

**GREEN.** After the implementation: `tests/unit/context`, the tables, features and pipeline suites pass; `make lint`
and `make typecheck` clean.

## What was decided / found along the way

- **OKX gets ten levels** by using `books` (400 levels, snapshot plus updates with a `prevSeqId` chain) and not `books5`.
  The existing normalizer and `BookService` already handle that chain; the cost is the delta traffic, measured after
  deployment, and `books5` remains the fallback with the imbalance then absent for OKX.
- **A book is of the series' own market**: Binance's series are spot, so their book is the spot partial-depth stream,
  not the perpetual's; the pass looks it up by the series' own venue and symbol and never through the perpetual the
  derivatives are shown from. The two coincide in name today and not in meaning.
- **Mutations found five test gaps**, each now closed: a crossed book would have become a quote (the first version of
  the test used a non-contiguous sequence id, so the book was invalid for another reason and the crossing was never
  exercised); the OFI window being longer than a minute; the quote time; a symbol not watched getting a book; Bybit
  asking for the first symbol only.
- **Survivors that are equivalent**: the grace before the clock closes a silent minute; an extra observation at an empty
  minute's boundary (the same flow, timestamped at the same later observation); a sequence gap not breaking the
  baseline separately from the reset the task calls on reconnect; and a few second guards on facts that hold by
  construction.
- The sampling is a stated limit, not a hidden one: the OFI is of what a sampled book did, not the event-level figure,
  and the registration says so.

## What is still open

- **Host load** with five books, a liquidation socket and three REST polls on a shared machine is unmeasured until
  the deployment (SC-006); the plan's fallback is `orderbook.1` for Bybit.
- **Binance spot depth carries no timestamp**, so its minutes are dated by receipt: stated in the normalizer where it
  already was, and the one place event time and receive time coincide by necessity.
- The collectors carry the previous image until rebuilt, and the worker the previous pass.
