# Contract: `VenueConnector`, `StreamSession`, and `rejection()`

No HTTP surface changes. These are module boundaries, and the seams the spec says
the earlier tests missed.

## `VenueConnector` (extended)

```python
class VenueConnector(Protocol):
    def connect(self, streams: Sequence[str]) -> None: ...
    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...
    def drain_frames(self) -> list[str]: ...
    @property
    def frames(self) -> queue.Queue[str]: ...
    @property
    def alive(self) -> bool: ...          # NEW
```

**`alive`** is true from the moment `connect` has started the reader until the reader
returns for **any** reason, and false after `close()`. It is a fact about the reader,
not about the venue: a reader that is running but has never been subscribed
successfully is alive.

Implemented by `BinanceConnector` (delegating to `WebsocketTransport.alive`),
`BybitConnector`, `OkxConnector`, and by every test fake. A fake that omits it fails
`test_protocol_has_required_methods`.

**When a reader ends it logs why, once, at WARNING** — with the venue and the exception
text, or "closed by the venue" with the close code and reason. A reader never exits
silently. For `WebsocketTransport`, whose `_run` stores a failure in `_failure`, the
failure is logged where it is stored; today it is read only by `connect()`.

## `rejection(venue, frame) -> str | None`

Pure, in `connectors/venue.py`.

- Returns the venue's own message when `frame` is that venue's refusal, else `None`.
- Never raises: a frame that is not JSON, or has another shape, is `None`.
- A reader calls it on **every** frame, logs a non-`None` result at WARNING as
  `"<venue> rejected the request: <message>"`, and **queues the frame regardless**, so
  the archive keeps what the venue said.

| venue | recognised as | message returned |
|---|---|---|
| okx | `event == "error"` | `msg` |
| bybit | `success is False` | `ret_msg` |
| binance | — | always `None` |

Pinned against frames captured live on 2026-10-02:

```json
{"event":"error","msg":"Subscribe failed, wrong URL or channel:trades,instId:trades.BTC-USDT-SWAP doesn't exist. Please use the correct URL, channel and parameters referring to API document.","code":"60018","connId":"b2b0944b"}
{"success":false,"ret_msg":"error:handler not found,topic:publicTrade.NOTASYMBOL","conn_id":"…","req_id":"","op":"subscribe"}
```

Binance is `None` by design: no rejection frame has been observed for it.

## `StreamSession`

```python
tick() -> None        # called every 200 ms by the ingest loop; must not block
```

`tick` reconnects, in this order, when:

1. `now - connected_at >= policy.stream_lifetime_ns` — lifetime;
2. `not connector.alive` — the reader has ended;
3. `now - last_inbound > limit` — silence, with `limit` as defined in the data model.

A reconnect is attempted only at or after `next_attempt_ns`. It **never raises**: a
`connect()` that raises is caught, counted, logged, and scheduled. (`start()` still
raises, so a daemon that cannot connect at all fails loudly at start-up.)

**Guarantees**

1. **No venue is exempt.** A fake connector whose reader dies **without** a close frame,
   under a policy with `announces_close=True`, is reconnected. Today it is not.
2. **Attempts are never closer than** `min_connect_interval_ns`, and after *n* consecutive
   failures never closer than `min(min_connect_interval_ns × 2ⁿ, max_connect_backoff_ns)`.
3. **Logging is bounded.** One WARNING on entering DOWN; further failures log at attempts
   1, 2, 4, 8…; one INFO on recovery stating the attempts and the time down. For *N* ticks
   in a persisting condition the number of lines is O(log *N*), and 0 once it clears.
4. **Binance's lifetime fires.** With a fake clock advanced past 24 h, `tick` reconnects.
5. **State survives a reconnect.** The bars builder and the archive buffer belong to the
   daemon, not the socket: a reconnect loses no buffered frame, and the gap is the log line.

**Non-guarantee, stated**: silence counts any inbound frame, and a Bybit or OKX pong is
one. A venue that has rejected the subscription but still answers pings is not silent;
that case is the rejection log's.

## `build_daemon` (the seam)

The only place the three venues' endpoints are decided is `VENUE_REGISTRY`.
`build_daemon` takes `url` and `subscribe_message(symbols)` from it, builds the
connector, and applies `CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS` with
`dataclasses.replace(policy, max_silence_ns=…)`.

Tested by reading `connector._url` and `connector._subscribe_msg` off the connector
**the daemon built**:

| venue | `_url` | subscribe message names |
|---|---|---|
| okx | `wss://ws.okx.com:8443/ws/v5/public` | `{"channel":"trades","instId":"BTC-USDT-SWAP"}` |
| bybit | `wss://stream.bybit.com/v5/public/linear` | `publicTrade.BTCUSDT` |
| binance | built from the streams | none (URL-subscribed) |
