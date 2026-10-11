---
id: REQ-WP-095
title: "The order-flow panes (OFI, depth imbalance) and the venues' quotes are fed by a top-of-book subscription"
type: work-package
prd_ref: "§10.3, §15.1, §15.3, §17.1, §27.3; owner's direction 2026-10-11"
prd_lines: "891-902, 2338-2385, 4423-4436"
phase: null
status: specified
depends_on: [REQ-WP-093, REQ-WP-027, REQ-WP-084]
tags: [order-book, ofi, depth, quotes, collector, panes]
hard_gated: false
---

## Requirement

`OFI (1m)` and `Depth imbalance (10)` read "no data", and so does the cross-venue consensus
([[REQ-WP-091]]) whose own requirement says "no venue's mid is available at all". The cause is one thing: **the
ingest subscribes to trades only**, so there is no order book anywhere in the system. The consumers exist
(`features/ofi.py`'s `OFITracker`, `features/instant.py`'s `depth_imbalance_levels`, `book/service.py`'s
`BookService`, `tables/quotes.py`) and have no feed.

This requirement adds, to the collector of [[REQ-WP-093]]:

1. **A book subscription per venue**, public and keyless, probed from this host on 2026-10-11:
   Binance partial depth `<symbol>@depth<N>@<interval>`, Bybit `orderbook.<N>.<symbol>`, OKX `books5`/`books`.
   **Snapshot-style streams are used on purpose** where the venue offers them: each frame is the whole top of the
   book, so there is no delta stream to reconstruct and no sequence gap to recover from (§11.1's local book
   reconstruction is not needed to read the top ten levels). A frame is normalised into the project's
   `BookSnapshot`.
2. **Per-minute book summaries, computed in event time.** For each symbol the collector feeds the existing
   `OFITracker` and `BookService` and, when the first frame of the next minute arrives, finalises the minute that
   just ended using only frames with `event_time` before the boundary: the 1-minute OFI (§15.3's window), the
   depth imbalance over the top 10 levels (§15.1's `DI_10`), the top-of-book quote (bid, ask, mid) as of the
   boundary, and **how many frames the minute rested on**. They are stored in an append-only table; the quote
   also in the existing `quotes` table, which is what the consensus reads.
3. **The worker writes `ofi_1m` and `depth_imbalance_10` per bar**, as of the bar's close, from the minute
   summary that closed at or before it, for every timeframe.

Rules that hold:

- **No look-ahead**: a minute is finalised from frames before its closing boundary; the worker reads summaries
  with `close <= bar close`.
- **A thin minute is not a balanced one.** `OFIWindow` already carries its observation count because "zero flow
  and no data both read as 0". A minute with no frames (a reconnect) is stored with a count of zero and the
  worker writes **nothing** for it.
- **The sampling rate is a stated limit, not a hidden one.** The streams are snapshots at 100-1000 ms, so the OFI
  here is top-of-book OFI computed from sampled snapshots, not from every book event. It is a real measurement
  of what the sampled book did and not the exchange's full event-level OFI; the feature's registration says so.
- **Two market types, not one book**: Binance's series is a spot market and the book subscribed to is its spot
  book (the same stream host the trade ingest uses); Bybit's and OKX's are perpetuals and their books are the
  perpetual's. No book is attributed to a market it is not.

## Acceptance

- For a recorded frame of each venue the normaliser yields the expected `BookSnapshot` (best bid below best ask,
  levels ordered, quantities positive); a crossed or empty book is refused with a reason, never stored.
- For a scripted frame sequence across a minute boundary the stored minute carries the OFI, the depth imbalance
  and the mid a hand calculation gives; the frames after the boundary do not change it (a test).
- A reconnect produces a minute with a zero count and no feature rows for it.
- The writer's `ofi_1m` and `depth_imbalance_10` at a bar's close equal the stored summary of the last minute
  closed at or before it, and are unchanged when later summaries are appended (a test).
- `quotes` rows exist for each subscribed market at each minute close, with exchange time and receive time apart.
- On the running stack the two panes are enabled for the Binance, Bybit and OKX BTC series and the recorded
  query shows values inside their bounds ([-1, 1] for the imbalance).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-147-book-subscription]]
- **Outcomes:** [[OUT-2026-10-11-spec-live-panes]]
<!-- trace:end -->

## Notes

Host load is a constraint, not an afterthought: five books at 100 ms in Python on a machine that also runs the
live stack and other projects. The plan measures the collector's CPU before and after, and chooses the
interval that the host can carry. A slower stream is an honest trade; a starved MinIO is not
([[REQ-INFRA-012]]).
