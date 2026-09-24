# Implementation Plan: The ingest daemon runs for Bybit and OKX

**Branch**: `121-multi-venue-ingest` | **Date**: 2026-09-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/121-multi-venue-ingest/spec.md`

## Summary

The ingest daemon currently knows only Binance: one `url_for` (streams in URL), one `streams_for` (Binance `@aggTrade`), one `VenuePolicy` (`BINANCE`), and the daemon's venue is a constant. This feature makes the venue a value that flows through the entire live path: configuration → stream builder → subscription mechanism → session policy → archive prefix → `venue` column.

The core design tension is the **subscription seam**: Binance puts streams in the URL; Bybit V5 and OKX v5 subscribe by sending a JSON message *after* connecting. The transport layer currently assumes URL-only subscriptions (`url_for(streams)`). This feature introduces a **venue connector** abstraction that owns the full connection lifecycle (URL + optional post-connect subscription), so the session and daemon stay venue-agnostic.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5 (frontend unchanged).

**Primary Dependencies**: `websockets` (already), `aiohttp` (not needed), `pyyaml` (config). No new dependency.

**Storage**: No new tables; uses existing `bars`, `frames` archives.

**Testing**: pytest + unittest.mock for Python; integration tests hit fake transports. No live exchange access in CI (ADR-063).

**Target Platform**: existing Docker stack; two new services (`ingest-bybit`, `ingest-okx`).

**Performance Goals**: same throughput as Binance daemon; subscription adds one round-trip at connect.

**Constraints**:
- Binance behaviour must stay byte-identical (SC-005: existing tests pass unchanged).
- No venue constant in wiring path (FR-001, SC-004).
- Each venue's stream/subscription rule pinned by test to its docs (FR-002).
- A connection that delivers nothing is reported, not silent (FR-006).
- Live verification against Bybit/OKX is a deployment step, not a CI gate (ADR-063).

**Scale/Scope**: three venues × symbols × timeframes. One process per symbol per venue. No new tables.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | How this design satisfies it |
|---|---|
| **I. No look-ahead** | The daemon only uses data available at the moment of decision; no future data in subscription or reconnect logic. |
| **II. Time is not one thing** | `event_time` from trade frames; subscription and reconnect use local clock only for timeouts, never for event timestamps. |
| **III. History is immutable** | Raw frames and bars are never rewritten; silence reports are new records. |
| **IV. Baselines before models** | No ML here. |
| **VII. Live and replay are the same code** | The venue connector is used by both live daemon and replay (which fakes transport). |
| **IX. No automatic execution** | Ingest only produces bars; no orders. |
| **X. Thresholds are configuration** | Idle timeout, silence window, connect interval all come from `VenuePolicy`/config. |
| **XI. Results are reproducible** | Venue connector is pure enough for unit tests with fake transports. |
| **XII. Correctness precedes performance** | Subscription round-trip adds one RTT at connect — acceptable. |
| **XIII. Work is incremental** | Venue connector added, then each venue plugged in. |
| **XIV. Everything is traceable** | Every source file `# @trace: REQ-WP-076`; tests `@pytest.mark.trace("REQ-WP-076")`. |

No violations. No complexity to track.

## Key decisions

### 1. The subscription seam: a `VenueConnector` protocol

**Decision**: Introduce a `VenueConnector` class that wraps `WebsocketTransport` and owns the full connection lifecycle for one venue:

```python
class VenueConnector(Protocol):
    """What a venue needs to connect, subscribe and stay alive."""
    def connect(self, streams: Sequence[str]) -> None:
        """Open socket, send subscription if venue requires it, start reader thread."""
    def send(self, payload: str) -> None: ...
    def pong(self) -> None: ...
    def close(self) -> None: ...
    @property
    def frames(self) -> queue.Queue[str]: ...
```

Three implementations: `BinanceConnector` (URL-only, current behaviour), `BybitConnector` (connect + send V5 subscribe JSON), `OkxConnector` (connect + send v5 subscribe JSON).

`WebsocketTransport` becomes an internal detail of `BinanceConnector`; other connectors wrap a plain websocket + their subscribe logic.

**Rationale**: The session (`StreamSession`) only calls `connector.connect(streams)`, `connector.frames`, `connector.pong()`, `connector.close()`. It never knows whether the venue subscribed via URL or post-connect message. This keeps `StreamSession` unchanged except for taking a `VenueConnector` instead of `WebsocketTransport`.

**Alternatives considered**:
- Extend `WebsocketTransport` with optional post-connect hook — rejected: conflates two different connection shapes; a Bybit connector has no URL params, an OKX connector has neither URL params nor Binance-style streams.
- Put subscription logic in `StreamSession` — rejected: session would grow venue-aware branches; violates FR-001 (venue as a value, not scattered conditionals).

### 2. Venue configuration in `ingest_main`

**Decision**: `CHANNELFLOW_INGEST_VENUE` env var (required, one of `binance`, `bybit`, `okx`). `CHANNELFLOW_INGEST_SYMBOLS` stays one symbol per process. `ingest_main` reads venue, looks up policy and stream builder from a registry, builds the appropriate `VenueConnector`, and passes it to `IngestDaemon`.

**Rationale**: One env var per process, same shape as `CHANNELFLOW_INGEST_SYMBOLS`. No new config file; stays consistent with existing `CHANNELFLOW_INGEST_SYMBOLS`/`CHANNELFLOW_INGEST_TIMEFRAME_NS`.

### 3. Stream/subscription builders per venue

**Decision**: Add `streams_for_venue(venue, symbols)` and `subscribe_message(venue, streams)` to `connectors/websocket.py` (or new `connectors/venue.py`). Each returns the venue's exact strings.

**Rationale**: Single place for the exact strings; tests assert byte-for-byte against docs.

### 4. `VenueConnector` implementations

- **Binance**: wraps `WebsocketTransport` with `binance_stream_url`; no post-connect message.
- **Bybit**: plain websocket to `wss://stream.bybit.com/v5/public/linear`; on `open`, sends `{"op": "subscribe", "args": [...]}`. Ping payload `{"op":"ping"}`, expects `{"op":"pong"}` (not measured for pong).
- **OKX**: plain websocket to `wss://ws.okx.com:8443/api/v5/market`; on `open`, sends `{"op": "subscribe", "args": [{"channel": "trades", "instId": "..."}]}`. Ping payload `ping`, expects `pong` (bare string).

### 4. Archive prefix and `venue` column

**Decision**: `FrameArchive` takes `venue` arg; prefix = `venue/` (e.g., `bybit/raw/cex/...`). `IngestDaemon` passes its venue to `FrameArchive`. `BarSink` already writes `venue` column; `IngestDaemon` passes its venue to `BarSink`.

### 5. Silence detection

**Decision**: `IngestDaemon` tracks `last_frame_ns` per `(venue, symbol)`. A background check (every `idle_timeout_ns` from policy) logs a warning if `now - last_frame > silence_window`. `silence_window_ns` configurable (default: `idle_timeout_ns * 2`). Reported via structured log (venue, symbol, last_frame, silence_duration); does not raise.

### 6. Compose services

**Decision**: Two new services in `docker-compose.yml`:

```yaml
ingest-bybit:
  command: ["python", "-m", "channelflow.pipeline.ingest_main"]
  environment:
    CHANNELFLOW_INGEST_VENUE: bybit
    CHANNELFLOW_INGEST_SYMBOLS: ${CHANNELFLOW_INGEST_SYMBOLS_BYBIT}
    ...
  depends_on: [postgres, minio]

ingest-okx:
  command: ["python", "-m", "channelflow.pipeline.ingest_main"]
  environment:
    CHANNELFLOW_INGEST_VENUE: okx
    CHANNELFLOW_INGEST_SYMBOLS: ${CHANNELFLOW_INGEST_SYMBOLS_OKX}
    ...
```

`.env.example` gets `CHANNELFLOW_INGEST_SYMBOLS_BYBIT` and `_OKX` (default empty; `ingest_main` refuses empty).

### 5. Tests

- Unit: venue connector factories, stream builders, subscription payloads (byte-for-byte against docs), silence detector, venue registry.
- Integration: fake transport per venue; asserts connection, subscription, frames, silence report.
- Existing Binance tests pass unchanged (SC-005).

## Project Structure

### Documentation (this feature)

```text
specs/121-multi-venue-ingest/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── transport.md
│   ├── connector.md
│   └── pipeline.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/channelflow/connectors/
├── venue.py                 # NEW: VenueConnector protocol + registry
├── websocket.py             # + bybit_stream_url, okx_stream_url, subscribe_message
├── session.py               # StreamSession takes VenueConnector
├── bybit/
│   ├── connector.py         # NEW: BybitConnector
│   └── __init__.py
├── okx/
│   ├── connector.py         # NEW: OkxConnector
│   └── __init__.py
└── binance/
    ├── connector.py         # NEW: BinanceConnector (wraps WebsocketTransport)
    └── ...

src/channelflow/pipeline/
├── ingest_main.py           # + venue config, registry lookup
└── ingest.py                # IngestDaemon takes VenueConnector + venue str

src/channelflow/pipeline/archive.py  # FrameArchive takes venue prefix

tests/
├── unit/connectors/
│   ├── test_binance_connector.py
│   ├── test_bybit_connector.py
│   ├── test_okx_connector.py
│   ├── test_venue_registry.py
│   └── test_silence_detector.py
└── integration/
    └── test_multi_venue_ingest.py   # NEW: fake transport per venue
```

**Structure Decision**: `connectors/` becomes a package with submodules per venue; `venue.py` is the registry. `StreamSession` changes signature from `WebsocketTransport` to `VenueConnector` — one-line change in `ingest.py`.

## Complexity Tracking

No violations to justify.

---

## Phases

- **Phase 0** — `research.md`: protocol details for Bybit V5 / OKX v5 (subscription messages, ping/pong, stream naming), measured idle timeouts.
- **Phase 1** — `data-model.md`, `contracts/`, `quickstart.md`.
- **Phase 2** — `/speckit-tasks` → `tasks.md`.

---

## Notes

- The subscription seam is the single architectural decision; everything else flows from it.
- No live exchange access in CI; tests use `FakeTransport` that records sent/received.
- Binance behaviour is frozen: its tests are the regression guard.
- A venue that connects and delivers nothing is **visible** — the silence detector ensures this, and the requirement's motivating incident (upper-case stream name on Binance) will never be silent again.
- Symbol spellings are not translated; a misconfigured symbol surfaces as the silence report, not a guessed translation (FR-002, FR-006).