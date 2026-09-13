---
id: OUT-2026-09-13-implement-ingest-daemon
step: implement
records: [REQ-WP-066]
commit: null
---

## What was done

`connectors/websocket.py`, `pipeline/archive.py`, `pipeline/ingest.py` and its
composition root, plus the `ingest-binance` service. 29 tests, **19 of 19
mutants caught** across two sweeps.

**The stack now feeds itself.** Run against the live venue and then in the
compose stack: the API serves BTCUSDT bars built from a socket opened minutes
earlier, through the same path the browser uses, and the raw frames are in the
object store one compressed object per minute.

## The loop's shape came from a measurement

Binance sends a protocol PING every 20 seconds — intervals 20.0, 20.1, 19.9,
20.1 over 400 seconds — and drops a client that does not answer. `websockets`
answers automatically, but from the connection's own task, which runs only while
its event loop does.

So normalising, gzipping or committing on that loop would stop the pongs and the
venue would drop us **with no error and no close frame**. The socket therefore
runs in its own thread doing nothing but I/O, and everything expensive happens
across a queue. The queue's depth is a counter, so a consumer that cannot keep up
is a number rather than memory growth nobody attributes.

Measured in the live run: 76 frames in 20 seconds, queue never deeper than 24.

## A claim I made before measuring it

I wrote "measured, not read: an upper-case name connects and delivers nothing"
into a comment **before measuring it**. That was wrong to write, whatever it
turned out to be.

Measured afterwards: `btcusdt@aggTrade` delivers 48 frames in twelve seconds and
`BTCUSDT@aggTrade` delivers **zero**, connecting successfully and staying
silent. The claim was right and the order was not, and the test now pins it —
a silent subscription is the worst shape this could take, indistinguishable from
a quiet market.

## The archive is objects, not a table

§6.4.4 lays out `raw/cex/...` and line 642 says raw payloads "may remain plain
compressed objects/Parquet when Iceberg metadata adds no value". It adds none: a
frame has no schema to evolve and arrives ten times a second.

Measured: 800 frames a minute for one symbol, 395 KiB, **556 MiB a day raw**,
and gzip takes that to 12.3% — 68 MiB a day. The compression is what makes the
tier affordable, so it is not optional.

**Frames are stored uninterpreted.** §6.4.4's example splits the zone into
`cex/trades/` and `cex/book_deltas/`, which would mean reading each payload to
route it — normalisation, performed by the one component whose purpose is to be
free of it. A frame names its own stream; the archive keeps venue and minute and
lets the reader route. Stated as a deviation rather than done quietly.

## What the sweep found nothing asserting

Four things, all of them assertions I had not written rather than defects:

- a frame that parses but fails normalisation was counted by nobody, so a trade
  could silently never happen;
- no test checked that the session sees each frame — a daemon that took frames
  without telling it would reconnect a healthy connection on the one venue where
  silence is the only signal;
- the shutdown order was asserted as "both happened", not as "commit, then
  close", which is the difference between a gap in the shutdown and an apparent
  gap in the data;
- the archive's buffer being cleared after a write was untested, so every object
  could have repeated the previous one's frames and a re-normalisation would
  count each trade twice.

## Guards that fired, correctly

`test_the_compose_file_declares_the_services_that_exist` asserted that
`ingest-binance` was **not** in the compose file, with the reason. It failed
here, which is what it was for. `worker` stays absent.

The mutation harness also refused a specification whose source had moved: the
settings were lifted out of `api/main.py` into `channelflow/settings.py` so the
daemon and the API read one configuration rather than two, and the spec followed
the code rather than silently testing nothing.

## What this does not deliver

Only `@aggTrade` becomes events. Depth is archived and counted as ignored: bars
need trades, and a book this build does not maintain would be a half-built one.

A live daemon gives one candle per timeframe, so a chart is empty until the
first bar closes. Seeding history is separate work, and it is not a shortcut:
`Bar` refuses a venue kline outright, because it requires `low_time_ns`,
`high_time_ns`, `first_trade_id` and `last_trade_id`, which a kline does not
carry. The model will not let the venue's aggregation pass as ours.
