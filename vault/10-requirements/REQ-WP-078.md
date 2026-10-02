---
id: REQ-WP-078
title: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded
type: work-package
prd_ref: "§6.2, §6.4.4, §32, §33, §35.6"
prd_lines: "405-420, 600-642, 4752-4781, 4783-4799, 4897-4905"
phase: null
status: draft
depends_on: [REQ-WP-076]
tags: [ingest, reliability]
---

## Requirement

[[REQ-WP-076]] is `implemented`, its tests are green, and on 2026-10-02 — six
days after it landed — the deployment it was written for looked like this:

| venue / symbol | state | evidence |
|---|---|---|
| Bybit BTCUSDT | working | newest 1m bar at 10:35, 8,743 bars |
| Binance BTCUSDT | **dead since 09-28 07:45**, container `Up` | silence of 356,633 s logged five times a second; nothing reconnects |
| Binance ETHUSDT, SOLUSDT | crash-looping, 8,534 restarts | `failed to resolve host 'postgres'` (a network fault, repaired separately) |
| OKX BTC-USDT-SWAP | **never delivered a frame** | no row with `venue = 'okx'` in `bars`, ever |
| raw archive | **wrong place, and one symbol in three per minute** | see defect 4 |
| logs | 6.6 GB for one service in six days | INFO on every trade, frame and step |

This requirement is the repair. PRD §6.2 puts one ingest service per venue in
the deployment, §6.4.4 gives the raw zone its layout, §32 and §33 list the
health signals a feed owes the rest of the system — "WS reconnect count",
"stale seconds", "reconnects", "stale feed count" — and §35.6 names reconnect
among what connector tests must cover. None of those is met by a connector that
dies once and stays dead without saying so.

### Six defects, each measured

**1. OKX cannot connect, and says nothing.** The daemon opens
`wss://ws.okx.com/api/v5/market`. That is a REST path prefix, not a socket:
connecting to it returns `HTTP 404`. The connector's thread swallows the
exception, so the log holds only the silence detector's warnings. Even at the
right URL, `okx_streams` returns `trades.BTC-USDT-SWAP` and
`okx_subscribe_message` puts that whole string into `instId`; OKX answers
`Subscribe failed, wrong URL or channel:trades,instId:trades.BTC-USDT-SWAP
doesn't exist`. Verified live from the host against
`wss://ws.okx.com:8443/ws/v5/public`: with `instId = BTC-USDT-SWAP` trades
arrive immediately; with the prefix the venue rejects the subscription.

**2. A connection that ends is never reopened — for two venues of three.**
`StreamSession.tick` reconnects on silence only when `not
policy.announces_close`, which is true for Bybit alone. Binance and OKX are
assumed to send a close frame, and the connector classes do not turn one into a
reconnect: their reader thread ends on any exception or close and nothing
notices that it has. For Binance, `WebsocketTransport._run` catches the
exception, stores it in `_failure` and returns — and `_failure` is read only by
`connect()`, on the first connection, never afterwards. A Binance daemon whose
socket dies is therefore a container that is `Up`, has no feed, and reports
nothing but a warning.

**3. The silence limit is a different quantity from the one it borrows.**
`IngestDaemon._check_silence` takes `policy.idle_timeout_ns` and doubles it. For
Bybit and OKX that field is "how long the venue tolerates a silent *client*" —
a few tens of seconds. For Binance, `venue.py` sets it to 24 hours, and the
threshold is therefore 48 hours: a Binance feed that went silent at 09-28 07:45
could not have been reported before 09-30 07:45 at the earliest. A 24-hour figure is Binance's **stream
lifetime**. `connectors/session.py`'s own `BINANCE` policy has exactly that:
`stream_lifetime_ns=24 * 60 * 60 * SECOND_NS` and no idle timeout. The
[[REQ-WP-076]] copy in `connectors/venue.py` moved the value into the wrong
field and dropped the lifetime, so the 24-hour reconnect `tick` was written to
perform no longer happens. Two registries now define each venue's policy with
different numbers (OKX: 30 s in one, 30.9 s in the other), and the live daemon
uses the one with the mistake.

**4. The raw archive is filed twice over, and under a key with no symbol in it.** `build_daemon` passes
`prefix=f"{venue}/raw/cex"` and `FrameArchive.key_for` then appends
`self.venue` again, so a frame lands at
`binance/raw/cex/binance/2026/10/02/1059.jsonl.gz` — the bucket root, not
`raw/cex/`. Measured through the S3 API: `raw/cex/binance/` holds 12,850 objects
and **stops at 09-26 07:25**; `binance/raw/cex/binance/` holds 2,892 and
`bybit/raw/cex/bybit/` 8,837, both current. PRD §6.4.4 lays the zone out as
`s3://channel-flow/raw/cex/…`, and everything that reads the archive —
`tools/record/parity_capture.py` and the replay it feeds ([[REQ-NRT-PARITY]]) —
looks there. The existing test, `test_archive_prefix.py`, builds a
`FrameArchive` with its **default** prefix and checks `key_for`, so it passes
against a wiring that has never used that prefix: it tests the class and not
the seam where the mistake is.

**And the key names no symbol.** `key_for` is `<prefix>/<venue>/<date>/<HHMM>`:
venue and minute, nothing else. That was enough while one process wrote one
venue. The deployment runs three Binance processes — BTCUSDT, ETHUSDT, SOLUSDT,
one each because `ingest_main` refuses more than one symbol — and all three
write `…/HHMM.jsonl.gz`. `store.put` replaces an object, so the last process to
flush a minute wins and the other two symbols' frames for it are gone.
Measured by opening sampled objects and reading the `stream` of every frame in
them: `09/20 12:00` holds 467 frames, all `ethusdt@aggtrade`; `09/23 09:30`
holds 430, all `btcusdt@aggtrade`; `09/25 15:00` holds 235, all
`solusdt@aggtrade`; the three most recent minutes read on 10-02 were `sol`,
`eth`, `sol`. Object count says the same thing from the other side: with three
writers the archive grew by **one** object a minute.

This began on 2026-09-17, when `ingest-binance-eth` and `ingest-binance-sol` were
added to the compose file to meet §5.1's three symbols; nobody — including the
change that added them — asked whether the three shared a key space. Bars and
channels are unaffected, because they are built from the live stream and not read
back from the archive. The raw tier is what suffers, and it is the tier §7
calls the source of truth "where re-normalization may be required": frames
overwritten there cannot be recovered. Of the 12,850 minute-objects under
`raw/cex/binance/`, those written from the day ETH and SOL were added until the
archive moved on 09-26 each retain one symbol of three, chosen by timing; the
first couple of hours on 09-17, when BTC ran alone, are whole.

**5. The log carries debugging output at INFO.** Per trade, per frame and per
200 ms step: `BarBuilder.add called for trade …`, `_finalize_ready: …`,
`Normalized 1 trade(s)`, `Received raw frame: …`, `FrameArchive.flush called …
frames=0`, `S3ObjectStore.put succeeded`. Measured container log sizes after
six days: Bybit 6.6 GB, OKX 502 MB, Binance 177 MB — and the silence warning
repeats at 5 Hz for as long as the condition lasts. Compose sets no log
rotation, so none of it is bounded.

**6. A failed connection and a rejected subscription are invisible.** Items 1
and 2 are the same fault seen from two sides: a thread that ends without a word
cannot be told from a quiet market, which is the failure mode this repository
has recorded more than once and decided against each time.

### What this deliberately does not do

- **No new metrics.** §33 lists "reconnects" and "stale feed count", and
  `docs/deployment.md` already records that nine of §33's eleven metrics have no
  producer ([[REQ-WP-055]]). Giving these two a producer without a dashboard to
  say so would repeat that. Reconnects and silence become **log events with a
  stated reason**; turning them into metrics is left open and named.
- **No change to the DNS repair.** The lost network aliases on `postgres` and
  `minio` and the hard-coded container addresses were fixed on 2026-10-02
  (`1cf4edb`); they are the cause of the ETH and SOL crash loop, not of anything
  here.

## Acceptance

- **OKX connects.** The OKX connector opens `wss://ws.okx.com:8443/ws/v5/public`
  and subscribes with `instId` set to the instrument as OKX names it
  (`BTC-USDT-SWAP`), pinned by a test over what the connector is *built with*,
  not over a helper's return value. On a running deployment, a trade frame
  arrives and a bar is committed — checked by hand against the live venue and
  recorded in the implement outcome note, because CI has no network.
- **A rejection is a warning that quotes the venue.** An `"event":"error"` frame
  from a venue, and a connection that fails to open, each log at WARNING with
  the venue and the venue's own message. A reader thread never exits without a
  log line saying why.
- **A connection that ends is reopened, for every venue.** Whatever ended it — a
  close frame, an exception, or silence — `StreamSession` reconnects, subject to
  `min_connect_interval_ns`. Proven with a fake connector whose reader dies
  **without** a close frame and whose venue has `announces_close=True`: today's
  shape for Binance and OKX, and the one `tick` ignores.
- **Silence is measured against its own limit.** A policy carries a maximum
  silence that is not its idle timeout. It is configuration (Principle X), with
  a default per venue written in the policy and a stated basis for each. A
  feed silent past it is reconnected, and the log says so once on entry and once
  on recovery rather than on every step.
- **Binance's 24-hour lifetime is honoured again.** `stream_lifetime_ns` is set
  on Binance's policy and the session reconnects when it elapses — proven with a
  fake clock advanced past 24 hours.
- **One definition of a venue's policy.** The two registries are reduced to one;
  a test fails if a venue's policy is defined in two places with different
  values.
- **The archive key is right where it is built.** A test constructs the daemon
  through `build_daemon` with the deployment's own `CHANNELFLOW_ARCHIVE_URI` and
  asserts the key of a written frame has the venue **once**, under `raw/cex/`,
  and names the symbol. A test that cannot fail on the mistake above is not this
  criterion.
- **Two symbols of one venue never share an object.** Two archives for different
  symbols of the same venue, flushed in the same minute, produce two objects, each
  holding only its own symbol's frames. Proven by reading the frames back, not by
  comparing key strings: the earlier mistake looked fine as a string.
- **The loss is stated, not hidden.** The implement outcome note records, per
  symbol, how many already-written minute-objects hold that symbol, so the extent
  of what was overwritten between 2026-09-17 and 2026-09-26 is a number somebody
  can read.
- **The misplaced objects are moved, not abandoned.** Objects already written —
  under `<venue>/raw/cex/<venue>/` and the 12,850 under `raw/cex/binance/` —
  are placed under the new layout by the symbol their own frames name, verified
  equal by size and checksum, and only then removed from the old location. An
  object holding more than one symbol is refused and left where it is. The counts
  before and after are recorded in the implement outcome note.
- **The log is bounded.** Nothing on the per-trade, per-frame or per-step path
  logs at INFO. A repeated condition does not repeat its line. Every service in
  `docker-compose.yml` carries a log size cap, and a test reads the file to
  prove none is without one. Measured log bytes per minute for each ingest
  service before and after are recorded in the implement outcome note.

## Trace

<!-- trace:begin -->
_Not yet generated. Run `make graph`._
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
