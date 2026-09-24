# Contract: `channelflow.connectors.venue`

The public surface for adding a venue.

```python
from typing import Protocol, Sequence, Callable
import queue

class VenueConnector(Protocol):
    """Full connection lifecycle for one venue."""

    def connect(self, streams: Sequence[str]) -> None:
        """Open socket, send subscription if needed, start reader thread."""
    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...
    @property
    def frames(self) -> queue.Queue[str]: ...

@dataclass(frozen=True)
class VenueConfig:
    connector: type[VenueConnector]
    stream_builder: Callable[[Sequence[str]], tuple[str, ...]]
    policy: VenuePolicy
    archive_prefix: str

VENUE_REGISTRY: dict[str, VenueConfig]
```

## `src/channelflow/connectors/websocket.py`

```python
def binance_streams(symbols: Sequence[str]) -> tuple[str, ...]
def bybit_streams(symbols: Sequence[str]) -> tuple[str, ...]
def okx_streams(symbols: Sequence[str]) -> tuple[str, ...]

def binance_subscribe_message(streams: Sequence[str]) -> str | None
def bybit_subscribe_message(streams: Sequence[str]) -> str
def okx_subscribe_message(streams: Sequence[str]) -> str
```

## `src/channelflow/connectors/bybit/connector.py`

```python
class BybitConnector:
    def __init__(self, url: str, subscribe_msg: str):
        ...
    def connect(self, streams: Sequence[str]) -> None: ...
    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...
    @property
    def frames(self) -> queue.Queue[str]: ...
```

## `src/channelflow/connectors/okx/connector.py`

```python
class OkxConnector:
    def __init__(self, url: str, subscribe_msg: str):
        ...
    # same methods as BybitConnector
```

## `src/channelflow/connectors/binance/connector.py`

```python
class BinanceConnector:
    def __init__(self, url_for: Callable[[Sequence[str]], str]):
        self._transport = WebsocketTransport(url_for=url_for)
    # delegates to _transport
```

## `src/channelflow/pipeline/ingest.py`

```python
class IngestDaemon:
    def __init__(
        self,
        *,
        venue: str,
        connector: VenueConnector,
        policy: VenuePolicy,
        clock: Clock,
        catalog: Catalog,
        archive_store: ObjectStore,
        archive_prefix: str,
    ):
        self.venue = venue
        self.session = StreamSession(
            connector=connector,
            policy=policy,
            clock=clock,
            on_frame=self._on_frame,
        )
        self.archive = FrameArchive(
            store=archive_store,
            venue=venue,
            prefix=f"{venue}/raw/cex",
        )
        self.sink = BarSink(
            table=bars.table_for(catalog),
            venue=venue,
        )
```

## `src/channelflow/pipeline/archive.py`

```python
class FrameArchive:
    def __init__(self, *, store: ObjectStore, venue: str, prefix: str):
        self.prefix = f"{venue}/{prefix.lstrip('/')}"
```

## `src/channelflow/pipeline/ingest_main.py`

```python
def main() -> int:
    venue = os.environ["CHANNELFLOW_INGEST_VENUE"]
    config = VENUE_REGISTRY[venue]
    symbols = parse_symbols(os.environ["CHANNELFLOW_INGEST_SYMBOLS"])
    streams = config.stream_builder(symbols)
    connector = config.connector(...)  # per-venue ctor
    daemon = IngestDaemon(
        venue=venue,
        connector=connector,
        policy=config.policy,
        ...
    )
    daemon.run()
    return 0
```

## `src/channelflow/settings.py` (addition)

```python
INGEST_VENUE = "CHANNELFLOW_INGEST_VENUE"
INGEST_SYMBOLS_BYBIT = "CHANNELFLOW_INGEST_SYMBOLS_BYBIT"
INGEST_SYMBOLS_OKX = "CHANNELFLOW_INGEST_SYMBOLS_OKX"
SILENCE_MULTIPLIER = "CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER"

def settings_from_env(...) -> Settings:
    ...
```

## `docker-compose.yml` (additions)

```yaml
ingest-bybit:
  build:
    context: .
    dockerfile: Dockerfile
  command: ["python", "-m", "channelflow.pipeline.ingest_main"]
  environment:
    CHANNELFLOW_CATALOG_URI: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    CHANNELFLOW_WAREHOUSE: s3://${MINIO_BUCKET}/warehouse
    CHANNELFLOW_S3_ENDPOINT: http://minio:9000
    CHANNELFLOW_S3_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
    CHANNELFLOW_S3_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
    CHANNELFLOW_S3_REGION: us-east-1
    CHANNELFLOW_INGEST_VENUE: bybit
    CHANNELFLOW_INGEST_SYMBOLS: ${CHANNELFLOW_INGEST_SYMBOLS_BYBIT}
    CHANNELFLOW_INGEST_TIMEFRAME_NS: ${CHANNELFLOW_INGEST_TIMEFRAME_NS}
    CHANNELFLOW_ARCHIVE_URI: s3://${MINIO_BUCKET}/raw/cex
  depends_on:
    postgres:
      condition: service_healthy
    minio:
      condition: service_healthy
  restart: unless-stopped

ingest-okx:
  # same, venue=okx, CHANNELFLOW_INGEST_SYMBOLS: ${CHANNELFLOW_INGEST_SYMBOLS_OKX}
```

## `.env.example` (additions)

```bash
# The ingest daemon's venue (REQ-WP-076). One venue per process.
CHANNELFLOW_INGEST_VENUE=

# Bybit symbols, one per process. Empty means the service is disabled.
CHANNELFLOW_INGEST_SYMBOLS_BYBIT=
# OKX symbols, one per process. Empty means the service is disabled.
CHANNELFLOW_INGEST_SYMBOLS_OKX=

# Silence window multiplier (default 2.0). Silence = idle_timeout * multiplier.
CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER=2.0
```