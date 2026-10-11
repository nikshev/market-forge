---
id: OUT-2026-10-11-plan-live-panes
step: plan
records: [REQ-WP-093, REQ-WP-094, REQ-WP-095, REQ-WP-096, REQ-WP-097]
commit: null
---

## What was done

Planned [[REQ-WP-093]] to [[REQ-WP-097]] in `specs/145-149`: a `plan.md` and a `tasks.md` each (tests first; the RED
output goes into each implementation outcome note). The family shares one runtime (`channelflow.context`) built
in spec 145 and reused by 146 and 147; 148 is one worker pass over what 147 writes; 149 is a read-only tool plus
the recorded acceptance.

## What was decided

- **The shared runtime is built once, in spec 145**, and 146/147 add streams to it. A second per-spec runtime
  would be three ways to reconnect.
- **The existing `StreamSession` and `WebsocketTransport` are reused** for the liquidation and book sockets. They
  already decide when to reconnect, ping and give up, and are tested on a fake clock; the lesson written into
  them (the socket's thread must do nothing but I/O, because Binance drops a client that misses its 20-second
  pong) applies to the collector unchanged.
- **Funding is the venue's settled history**, loaded at start and refreshed hourly; polled states never enter
  `funding_z`. Found while planning: `settled_funding` returns every state whose settlement passed -- one per
  poll -- so a 24-observation window over polled states is 24 estimates of one interval. The writer filters to the
  history rows before calling the library, and spec 145 was amended before it was committed.
- **Staleness constants are named in `context/sources.py`, each with its reason**, not the library's 5-minute
  default (right for polled values, wrong for an 8-hour settlement and for Binance's 5-minute USD open interest).
- **Bybit's book is not snapshot-only** (a snapshot then deltas); the existing `BookService` handles that and is
  read once a second, so all venues share one sampling. OKX's `books5` has five levels, so a ten-level imbalance
  is written only where a venue's book has ten; ADR-070 and spec 147 were corrected to say so.
- **Evidence for the liquidation parsers**: OKX frames were recorded (a long liquidated is `posSide=long,
  side=sell`); Binance and Bybit were silent for four minutes. If a recording cannot be had, that parser's test
  is built from the venue's documentation and **says it is documented, not recorded**.
- **A funding value is never a polled estimate** and **a quiet minute is a reading only where the collector was
  listening** -- both are tested, not stated.

## What is still open

- The worker rebuild is held until the worker pass has been replayed against the real lakehouse without writing;
  the order of deployment is collectors first, worker last.
- Host load with the book streams is unmeasured until T003 of spec 147 takes its baseline.
- Whether the Binance panes (spot, no consensus) should be given a second spot venue is the owner's call.
- DEX panes remain unplanned.
