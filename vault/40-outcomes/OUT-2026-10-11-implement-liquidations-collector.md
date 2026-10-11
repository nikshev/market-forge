---
id: OUT-2026-10-11-implement-liquidations-collector
step: implement
records: [REQ-WP-094]
commit: null
---

## What was done

Implemented [[REQ-WP-094]] (spec 146) as far as the repository goes. Status is `tested`: the pane enabled on the
running stack for series whose venue stored a liquidation (SC-004) is a measurement of the deployment.

- **Parsers**, one per venue, pure: Binance `forceOrder`, Bybit `allLiquidation`, OKX `liquidation-orders`.
- **Table** `liquidations`: events and the stream's heartbeat in one table (`kind`), each stored once across a
  reconnect replay or a restart.
- **Stream task** (`context/streams.py`) over the existing `StreamSession`: a bad frame never stops the stream; a
  heartbeat per symbol per minute only for a minute the connection stayed up for; the silence limit off for the
  quiet Binance stream, its keepalive not.
- **The venue streams** (`context/liquidations.py`): what to connect to and what to store; wired into the collector
  (`Collector` steps its streams and commits their sinks with the polls; `CHANNELFLOW_CONTEXT_STREAMS`).
- **The worker pass** writes `liquidation_long_usd_5m`, `liquidation_short_usd_5m`, `liquidation_imbalance_5m` beside
  the derivatives features in the same single commit.
- **Mutation sweeps**: nine files, ~80 mutations; every survivor either killed by a test added for it or reasoned.

## Evidence

**RED first.** The tests were written and copied in before any module existed:

    ERROR tests/unit/connectors/test_context_liquidation_parsers.py
    ERROR tests/unit/tables/test_liquidations.py
    ERROR tests/unit/features/test_liquidation_values.py
    ERROR tests/unit/context/test_streams.py
    ERROR tests/unit/pipeline/test_context_pass_liquidations.py
    ImportError: cannot import name 'liquidations' from 'channelflow.tables'
    5 errors during collection

**GREEN.** After the implementation: `tests/unit/context` 73 passed, the connector, table, feature and pipeline
suites around them pass; `make lint`, `make typecheck` clean.

## What was decided / found along the way

- **Binance moved its futures websocket.** The legacy `/ws/` path connects and delivers nothing for `forceOrder`
  (and nothing for a `markPrice` control stream either, at the time of testing); `/market/ws/` delivers, and depth
  moved to `/public/ws/`. Found because ten minutes of silence on every symbol was implausible beside OKX's three
  events in four. A test pins the path. It means a silent connection is **not** evidence of a quiet market -- which is
  the argument for the heartbeat, one level up.
- **Coverage is the stream's heartbeat, not the REST poller's** (decided before any code; spec and requirement
  amended): the poller being up proves nothing about the socket.
- **Bybit's side is the position's; Binance's and OKX's is the order's.** Pinned per venue. The Bybit tests use the
  frame the venue's documentation shows, **named as documented, not recorded**: no BTC/ETH/SOL liquidation arrived on
  Bybit in four minutes, nor on eight symbols in ten.
- **OKX sizes are contracts**; the contract value comes from the instruments answer, and a watched instrument whose
  value could not be fetched is refused with its name rather than guessed.
- **Two of the five liquidation features are not produced** (intensity, time since a spike): no pane reads them, one
  needs volume a bar of another timeframe does not carry, the other a threshold nobody chose. The registrations say
  so; the requirement and spec were narrowed rather than the features faked.
- **A mutation found a missing test again**: an OKX frame of another channel carrying a watched instrument's data
  would have been parsed (the existing test used an empty item); a dead reader inside the session's reconnect
  throttle would still have written a heartbeat; a frame not shown to the session would have let the silence limit
  fire. Each now has a test.

## What is still open

- **Not deployed yet**: the collectors carry the old image until rebuilt; the stream starts with them.
- **Observed on the live stack** only after a few hours: how many events arrive, whether any BTC liquidation is seen on
  Binance/OKX in the range, and the pane's state.
- The heartbeat treats "reader alive and connection old enough" as listening; it cannot see a connection that is open
  and has silently stopped delivering. The venues' pings (and Bybit/OKX's pongs, counted as frames) are the guard.
