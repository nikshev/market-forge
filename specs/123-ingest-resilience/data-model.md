# Phase 1 Data Model: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded

No table changes and no schema changes: nothing here touches Iceberg. What follows
is the in-memory model and the object key, which is the only persisted shape that
changes.

## `VenuePolicy` (extended)

`connectors/session.py`. The one definition of what a venue expects of a client and
what this system tolerates from that venue.

| field | type | meaning | change |
|---|---|---|---|
| `venue` | `str` | | |
| `keepalive` | `Keepalive` | who pings | |
| `idle_timeout_ns` | `int \| None` | how long **the venue** tolerates a silent **client** | Binance: **removed** (was a 24 h stream lifetime in the wrong field) |
| `client_ping_interval_ns` | `int \| None` | | |
| `ping_payload` | `str \| None` | | |
| `stream_lifetime_ns` | `int \| None` | how long the venue keeps a connection regardless of traffic | Binance: **restored** (24 h) |
| `announces_close` | `bool` | whether the venue sends a close frame | documentation only; **no longer gates behaviour** |
| `min_connect_interval_ns` | `int` | shortest gap between attempts | |
| `max_silence_ns` | `int \| None` | how long **this system** tolerates a silent **venue** | **new**; 60 s on the three live venues |
| `max_connect_backoff_ns` | `int` | ceiling on the retry delay | **new**; 60 s |

**Validation** (`__post_init__`, additions only):

- `max_silence_ns`, when set, is positive.
- `max_silence_ns` is **greater than** `client_ping_interval_ns` when both are set: a
  limit shorter than the keepalive would reconnect a healthy quiet connection between
  two pongs.
- `max_connect_backoff_ns >= min_connect_interval_ns`.

**Invariant, enforced by a test and not by this file**: one `VenuePolicy` per `venue`
across every module of `channelflow.connectors`. The seven definitions that existed
become four (`BINANCE`, `BYBIT`, `OKX`, `HYPERCORE`).

**Effective silence limit**

```text
limit = policy.max_silence_ns
        if policy.max_silence_ns is not None
        else (policy.idle_timeout_ns if not policy.announces_close else None)
```

The `else` keeps HyperCore behaving as it did. `None` means no silence reconnect.

## `VenueConfig` (extended)

`connectors/venue.py`. What the daemon reads to build a connector. Registry only.

| field | type | meaning | change |
|---|---|---|---|
| `connector` | `str` | dotted path of the class | |
| `stream_builder` | `Callable[[Sequence[str]], tuple[str, ...]]` | stream **labels**, for the session and the log | |
| `policy` | `VenuePolicy` | imported from `session.py`, not redefined | |
| `archive_prefix` | `str` | | **removed**: the venue is added once, by the key |
| `url` | `str \| None` | the WebSocket endpoint; `None` where the URL is built from the streams (Binance) | **new** |
| `subscribe_message` | `Callable[[Sequence[str]], str \| None]` | the post-connect message, from **symbols** | **new** |

`stream_builder` and `subscribe_message` take different inputs on purpose. OKX's stream
label is `trades.BTC-USDT-SWAP` and its `instId` is `BTC-USDT-SWAP`; feeding the
first to the second is the defect. Each function takes the thing it is about.

## `ConnectionState` (inside `StreamSession`)

| field | meaning |
|---|---|
| `connected_at_ns` | when the last attempt began (existing) |
| `last_inbound_ns` | last frame of any kind (existing) |
| `consecutive_failures` | attempts since the connection last held, 0 when it does |
| `next_attempt_ns` | earliest instant the next attempt may begin |
| `down_since_ns` | `None` while the connection is healthy |
| `down_reason` | why it was last declared down: `reader ended`, `silent for <n> s`, `lifetime`, or the exception text from a failed `connect()` |

**Transitions**

```text
UP ──(reader ended | silent > limit | lifetime elapsed)──► DOWN(reason)
DOWN ──(attempt at/after next_attempt_ns)──► attempting
attempting ──connect() raised──► DOWN(failures+1, next = now + min(min×2ⁿ, cap))
attempting ──connect() returned──► UP   (logs recovery with failures, down_for)
```

`UP → DOWN` logs once, WARNING, with the reason. Failures log at attempts 1, 2, 4, 8…
`DOWN → UP` logs once, INFO. There is no per-step line in either state.

Note that `connect()` returning is not proof of a working connection for Bybit and OKX:
their `connect()` starts a reader thread and returns. A reader that then fails is
caught by `alive` on the next `tick` and goes `UP → DOWN` again, counting from the
failures already accrued, so backoff survives the false recovery.

## `ArchiveKey`

```text
raw/cex/<venue>/<symbol>/<YYYY>/<MM>/<DD>/<HHMM>.jsonl.gz
```

| part | source | rule |
|---|---|---|
| `raw/cex` | the path of `CHANNELFLOW_ARCHIVE_URI`, default `raw/cex` | passed through unchanged; not prefixed with the venue |
| `<venue>` | the registry key | appears **once** |
| `<symbol>` | `CHANNELFLOW_INGEST_SYMBOLS*`, as configured | non-empty, no `/`; not case-folded |
| date and `HHMM` | **receipt time**, UTC (Principle II) | unchanged from today |

Two processes archiving different symbols of one venue in the same minute write different
keys. The same process restarting inside a minute it had already written still
replaces that object with its tail; stated, not fixed.

## `MigrationDecision`

What `rekey` concludes about one object. Pure; built from the key and the object's frames.

| variant | fields | action |
|---|---|---|
| `Move` | `source`, `destination`, `symbol` | copy, verify, delete |
| `AlreadyThere` | `source`, `destination` | destination equals source: delete the source only |
| `Refuse` | `source`, `reason` | leave in place, print the reason |

`reason` is one of `several symbols: [...]`, `no attributable frame`, `destination holds
different bytes`, `key matches no known layout`. A closed set, so a report can count them.

## `MigrationReport`

| field | meaning |
|---|---|
| `scanned` | objects examined |
| `moved` | per `(venue, symbol)` count |
| `already_there` | count |
| `refused` | list of `(key, reason)` |
| `minutes_present` | per `(venue, symbol)`, distinct minutes now holding that symbol |
| `minutes_expected` | per `(venue, symbol)`, minutes between the first and last object seen |

`minutes_expected − minutes_present` is **the extent of what was overwritten**, per
symbol, as FR-014 requires. It is a lower bound on the loss — it cannot see minutes
before the first or after the last object — and is reported as such.

## Relationships

```text
VenueConfig ─ policy ─► VenuePolicy ◄─ limit, lifetime, backoff ─ StreamSession
     │                                         │ polls .alive
     └─ url, subscribe_message ─► Connector ───┘ (reader logs why it ends)
build_daemon ─ prefix, venue, symbol ─► FrameArchive ─► ArchiveKey
rekey ─ reads objects ─► MigrationDecision ─► MigrationReport
```
