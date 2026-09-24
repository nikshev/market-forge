# Phase 0 Research: Multi-venue ingest

## Bybit V5 WebSocket (linear perps)

**Source**: https://bybit-exchange.github.io/docs/v5/websocket/public/trade

- **Endpoint**: `wss://stream.bybit.com/v5/public/linear`
- **Subscribe**: after connect, send
  ```json
  {"op": "subscribe", "args": ["publicTrade.BTCUSDT"]}
  ```
  Channel format: `publicTrade.{symbol}` (symbol in Bybit format: `BTCUSDT`).
- **Trade message**:
  ```json
  {"topic": "publicTrade.BTCUSDT", "data": [{"T": 1234567890123, "p": "50000", "v": "0.1", "S": "Buy", "L": "", "i": "12345"}]}
  ```
  Fields: `T` (timestamp ms), `p` (price), `v` (size), `S` (side: "Buy"/"Sell").
- **Ping/Pong**: client sends `{"op": "ping"}`, server replies `{"op": "pong"}` (measured: both JSON).
- **Idle timeout**: ~60.7s with no close frame (measured 2026-09-12). Silence = drop.
- **Reconnect**: measured ~60s idle timeout. Bybit sends no close frame — silence = drop.

## OKX v5 WebSocket (swaps)

**Source**: https://www.okx.com/docs-v5/en/#websocket-api-public-channel-trade

- **Endpoint**: `wss://ws.okx.com:8443/api/v5/market`
- **Subscribe**: after connect, send
  ```json
  {"op": "subscribe", "args": [{"channel": "trades", "instId": "BTC-USDT-SWAP"}]}
  ```
  Channel: `trades`, `instId` format: `BTC-USDT-SWAP` (OKX uses dash and `-SWAP` suffix).
- **Trade message**:
  ```json
  {"arg": {"channel": "trades", "instId": "BTC-USDT-SWAP"}, "data": [{"instId": "BTC-USDT-SWAP", "tradeId": "123", "px": "50000", "sz": "0.1", "side": "buy", "ts": "1234567890123"}]}
  ```
  Fields: `ts` (timestamp ms), `px` (price), `sz` (size), `side` ("buy"/"sell").
- **Ping/Pong**: client sends `ping` (bare string), server replies `pong` (bare string).
- **Idle timeout**: ~30.9s with code 4004 (measured 2026-09-12).
- **Reconnect**: OKX sends close frame with code 4004 on idle.

## Binance (existing, frozen)

- **Endpoint**: `wss://stream.binance.com:9443/stream?streams=...`
- **Stream name**: `{symbol.lower()}@aggTrade` (lowercase, measured).
- **Trade message**: standard Binance aggTrade.
- **Ping/Pong**: protocol-level (handled by `websockets` lib).
- **Idle timeout**: 24h (Binance closes at 24h).

## Subscription seam options (decision recorded in plan)

| Layer | Pros | Cons |
|-------|------|------|
| `WebsocketTransport` extended with `subscribe` method | Keeps transport abstraction; session unchanged | Conflates URL + message logic in one class |
| `StreamSession` sends subscribe after `transport.connect()` | Session stays venue-aware; transport stays simple | Session grows venue logic; violates FR-001 |
| **`VenueConnector` protocol wrapping transport** | Session stays venue-agnostic; each venue owns its full connect+subscribe lifecycle | New abstraction; three classes |

**Decision**: `VenueConnector` protocol. Session takes `VenueConnector`, calls `connect(streams)`, reads `frames`. Binance uses `BinanceConnector(url_for=binance_stream_url)` (URL-only). Bybit/OKX implement full connect+subscribe.

## Symbol formats

| Venue | Configured symbol | Stream/subscribe arg |
|-------|-------------------|---------------------|
| Binance | `BTCUSDT` | `btcusdt@aggTrade` |
| Bybit | `BTCUSDT` | `publicTrade.BTCUSDT` |
| OKX | `BTC-USDT-SWAP` | `{"channel": "trades", "instId": "BTC-USDT-SWAP"}` |

Symbol spelling is **configured as the venue writes it**; no translation layer. Misconfiguration → silence report (FR-006).

## Silence detection

| Venue | Idle timeout | Close frame | Silence window |
|-------|-------------|-------------|----------------|
| Binance | 24h | yes | 48h (2×) |
| Bybit | ~60s | none | 120s |
| OKX | ~31s (code 4004) | yes (code 4004) | 62s |

Configurable via `CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER` (default 2.0). `IngestDaemon` checks `now - last_frame_ns > silence_window_ns` per venue/symbol.

## Venue registry

```python
VENUE_REGISTRY = {
    "binance": VenueConfig(
        connector=BinanceConnector,
        stream_builder=binance_streams,
        policy=BINANCE_POLICY,
        archive_prefix="binance",
    ),
    "bybit": VenueConfig(
        connector=BybitConnector,
        stream_builder=bybit_streams,
        policy=BYBIT_POLICY,
        archive_prefix="bybit",
    ),
    "okx": VenueConfig(
        connector=OkxConnector,
        stream_builder=okx_streams,
        policy=OKX_POLICY,
        archive_prefix="okx",
    ),
}
```

`ingest_main` reads `CHANNELFLOW_INGEST_VENUE`, looks up config, builds connector, passes to `IngestDaemon`.

## Archive prefix

`FrameArchive(prefix=f"{venue}/raw/cex")` → objects under `s3://bucket/bybit/raw/cex/...`. Prevents cross-venue contamination.

## Symbol spelling

No translation. Configurable symbol must match venue's exact spelling. Misconfigured symbol → silence report (FR-006).

## Archive & bars venue column

`FrameArchive` takes `venue` → prefix. `BarSink` already takes `venue` (already in `Bar` model). `IngestDaemon` passes its `venue` to both.

## Live verification

Not in CI (ADR-063). Quickstart documents manual check: run daemon with real config, verify frames arrive, silence detector fires on bad symbol.

## Open questions (for planning, not spec)

- Should `VenueConfig` be a dataclass or a protocol? → dataclass (data-only).
- Where does `subscribe_message` live? → `connectors/venue.py` alongside registry.
- Connect rate limiting: `VenuePolicy.min_connect_interval_ns` used by `IngestDaemon` before reconnect attempt.
- Reconnect backoff: exponential with cap? Policy has `min_connect_interval_ns` (conservative).