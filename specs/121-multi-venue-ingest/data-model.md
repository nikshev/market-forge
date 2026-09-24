# Phase 1 Data Model: Multi-venue ingest

No new tables. Existing `bars` and `frames` archives carry the venue.

## `VenueConfig`

```python
@dataclass(frozen=True)
class VenueConfig:
    connector: type[VenueConnector]
    stream_builder: Callable[[Sequence[str]], tuple[str, ...]]
    policy: VenuePolicy
    archive_prefix: str
```

`VENUE_REGISTRY: dict[str, VenueConfig]` — key is the configured venue name.

## `VenueConnector` (protocol)

```python
class VenueConnector(Protocol):
    """Full connection lifecycle for one venue."""

    def connect(self, streams: Sequence[str]) -> None:
        """Open socket, send subscription if needed, start reader thread."""
    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...
    @property
    def frames(self) -> queue.Queue[str]: ...
```

## Implementations

| Venue | Class | Connect | Subscribe |
|-------|-------|---------|-----------|
| Binance | `BinanceConnector` | `WebsocketTransport(url_for=binance_stream_url)` | none (URL carries streams) |
| Bybit | `BybitConnector` | plain WS to `wss://stream.bybit.com/v5/public/linear` | sends `{"op":"subscribe","args":[...]}` on open |
| OKX | `OkxConnector` | plain WS to `wss://ws.okx.com:8443/api/v5/market` | sends `{"op":"subscribe","args":[{"channel":"trades","instId":...}]}` |

All three implement `VenueConnector`; `StreamSession` calls `connect(streams)`, reads `frames`, calls `pong()` on ping.

## `StreamSession` change

```python
class StreamSession:
    def __init__(
        self,
        *,
        connector: VenueConnector,  # was: transport: WebsocketTransport
        policy: VenuePolicy,
        clock: Clock,
        on_frame: Callable[[str], None],
    ):
```

Calls `connector.connect(streams)`; reads `connector.frames`; calls `connector.pong()` on ping.

## `IngestDaemon` changes

```python
class IngestDaemon:
    def __init__(
        self,
        *,
        venue: str,                          # NEW
        connector: VenueConnector,           # was: session: StreamSession
        ...
    ):
        self.venue = venue
        self.session = StreamSession(
            connector=connector,
            policy=policy,
            clock=clock,
            on_frame=self._on_frame,
        )
        self.archive = FrameArchive(store=..., venue=venue, prefix=f"{venue}/raw/cex")
        self.sink = BarSink(table=table_for(catalog), venue=venue)  # venue for Bar
        ...
```

## `FrameArchive`

```python
class FrameArchive:
    def __init__(self, *, store: ObjectStore, venue: str, prefix: str):
        self.prefix = f"{venue}/{prefix.lstrip('/')}"  # e.g. "bybit/raw/cex"
```

## `BarSink` and `Bar`

No schema change: `Bar.venue` already exists. `IngestDaemon` passes its `venue` to `BarSink`.

## Silence detector (in `IngestDaemon`)

```python
class IngestDaemon:
    def __init__(...):
        self._last_frame_ns: dict[tuple[str, str], int] = {}  # (venue, symbol) -> ns
        self._silence_window_ns = policy.idle_timeout_ns * SILENCE_MULTIPLIER

    def _on_frame(self, frame: Frame):
        key = (self.venue, frame.symbol)
        self._last_frame_ns[key] = frame.event_time_ns
        ...

    def _check_silence(self, now_ns: int):
        for (venue, symbol), last_ns in self._last_frame_ns.items():
            if now_ns - last_ns > self._silence_window_ns:
                logger.warning(
                    "silence detected",
                    venue=venue, symbol=symbol,
                    last_frame_ns=last_ns,
                    silence_ns=now_ns - last_ns,
                )
```

Called from a periodic timer (e.g., every 10s) or from the main loop.

## `VenueConfig` registry

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

`ingest_main` reads `CHANNELFLOW_INGEST_VENUE`, looks up `VENUE_REGISTRY[venue]`, builds connector, passes to `IngestDaemon`.

## Configuration

```bash
CHANNELFLOW_INGEST_VENUE=bybit          # required, one of [binance, bybit, okx]
CHANNELFLOW_INGEST_SYMBOLS=BTCUSDT      # one symbol per process
CHANNELFLOW_INGEST_TIMEFRAME_NS=60000000000
CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER=2.0  # optional
```

`.env.example` adds:
```
CHANNELFLOW_INGEST_SYMBOLS_BYBIT=BTCUSDT
CHANNELFLOW_INGEST_SYMBOLS_OKX=BTC-USDT-SWAP
CHANNELFLOW_INGEST_VENUE=               # required, no default
```

## Stream builders

```python
def binance_streams(symbols: Sequence[str]) -> tuple[str, ...]:
    return tuple(f"{s.lower()}@aggTrade" for s in symbols)

def bybit_streams(symbols: Sequence[str]) -> tuple[str, ...]:
    return tuple(f"publicTrade.{s}" for s in symbols)

def okx_streams(symbols: Sequence[str]) -> tuple[str, ...]:
    return tuple(f"trades.{s}" for s in symbols)  # channel name for OKX

def binance_subscribe_message(streams: Sequence[str]) -> str | None:
    return None  # Binance uses URL

def bybit_subscribe_message(streams: Sequence[str]) -> str:
    return json.dumps({"op": "subscribe", "args": list(streams)})

def okx_subscribe_message(streams: Sequence[str]) -> str:
    return json.dumps({"op": "subscribe", "args": [{"channel": "trades", "instId": s} for s in streams]})
```

## Connector implementations

```python
class BinanceConnector:
    def __init__(self, url_for: Callable[[Sequence[str]], str]):
        self._transport = WebsocketTransport(url_for=url_for)

    def connect(self, streams):
        self._transport.connect(streams)

    @property
    def frames(self):
        return self._transport.frames

    def send(self, payload):
        self._transport.send(payload)

    def pong(self):
        self._transport.pong()

    def close(self):
        self._transport.close()

class BybitConnector:
    def __init__(self, url: str, subscribe_msg: str):
        self._url = url
        self._subscribe_msg = subscribe_msg
        self._ws = None
        self._frames = queue.Queue()
        self._thread = None

    def connect(self, streams):
        self._ws = websockets.connect(self._url)
        self._ws.__enter__()
        self._ws.send(self._subscribe_msg)  # after connect
        # start reader thread...

class OkxConnector:
    # similar to Bybit, different URL and subscribe format
```

## `StreamSession` change (minimal)

```python
class StreamSession:
    def __init__(self, *, connector: VenueConnector, policy: VenuePolicy, clock: Clock, on_frame: Callable[[str], None]):
        self.connector = connector
        self.policy = policy
        self.clock = clock
        self.on_frame = on_frame

    def run(self):
        self.connector.connect(self.streams)
        while not self._stopping:
            frame = self.connector.frames.get()
            self.on_frame(frame)
            # pong logic uses connector.pong()
```

## `ingest_main` wiring

```python
def main():
    venue = os.environ["CHANNELFLOW_INGEST_VENUE"]
    config = VENUE_REGISTRY[venue]
    symbols = parse_symbols(os.environ["CHANNELFLOW_INGEST_SYMBOLS"])
    streams = config.stream_builder(symbols)
    connector = config.connector(
        url_for=... if binance else config.subscribe_message(streams),
    )
    daemon = IngestDaemon(
        venue=venue,
        connector=connector,
        policy=config.policy,
        ...
    )
    daemon.run()
```

## Compose services

```yaml
ingest-bybit:
  build: .
  command: ["python", "-m", "channelflow.pipeline.ingest_main"]
  environment:
    CHANNELFLOW_INGEST_VENUE: bybit
    CHANNELFLOW_INGEST_SYMBOLS: ${CHANNELFLOW_INGEST_SYMBOLS_BYBIT}
    CHANNELFLOW_INGEST_TIMEFRAME_NS: ${CHANNELFLOW_INGEST_TIMEFRAME_NS}
    # ... catalog, warehouse, S3
  depends_on: [postgres, minio]
  restart: unless-stopped

ingest-okx:
  # similar, venue=okx, CHANNELFLOW_INGEST_SYMBOLS_OKX
```