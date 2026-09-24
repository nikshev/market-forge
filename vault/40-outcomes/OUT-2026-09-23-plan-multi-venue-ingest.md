---
id: OUT-2026-09-23-plan-multi-venue-ingest
step: plan
records: [REQ-WP-076]
commit: 4486f291e2ad38d1aa1f41a38099820cdb1f41ad
---

## What was done

[[REQ-WP-076]] planned as `specs/121-multi-venue-ingest/`: `plan.md`,
`research.md`, `data-model.md`, `contracts/connector.md`, `quickstart.md`.

## What was decided

**The subscription seam is the single architectural decision.** Binance puts
streams in the URL; Bybit V5 and OKX v5 subscribe by a post-connect JSON
message. The `WebsocketTransport`'s `url_for(streams)` fits only Binance. The
plan introduces a `VenueConnector` protocol that owns the full connection
lifecycle (connect + optional post-connect subscribe), so `StreamSession`
stays venue-agnostic.

**Three `VenueConnector` implementations:**
- `BinanceConnector`: wraps existing `WebsocketTransport` (URL-only).
- `BybitConnector`: plain WS + post-connect `{"op":"subscribe",...}` (V5).
- `OkxConnector`: plain WS + post-connect `{"op":"subscribe",...}` (v5).

`StreamSession` changes from `WebsocketTransport` to `VenueConnector` — one
line change in `ingest.py`. `VenuePolicy` per venue already exists (measured
2026-09-12) and is reused.

**Configuration:** `CHANNELFLOW_INGEST_VENUE` + `CHANNELFLOW_INGEST_SYMBOLS_<VENUE>`
per `.env.example`. One process per symbol per venue, same refusal as Binance.

**Compose:** two new services (`ingest-bybit`, `ingest-okx`) reading the same
`.env` variable, same build as `ingest-binance`.

**Silence detection:** `IngestDaemon` tracks `last_frame_ns` per
`(venue, symbol)`; a background check every 10s reports silence if
`now - last_frame > silence_window_ns` (default `idle_timeout * 2`).

**Tests:** fake transport per venue; unit tests for connector factories,
stream builders, subscription payloads, silence detector. Binance tests
unchanged (SC-005).

**No backend storage change.** Uses existing `bars` and `frames` archives.

## What was rejected

- **Subscription logic in `StreamSession`**: would make the session
  venue-aware, violating FR-001 (venue as a value).
- **Extending `WebsocketTransport` with optional `subscribe` hook**:
  conflates two different connection shapes; Bybit/OKX have no URL params.
- **Per-row timeframe menu in markets view**: rejected in [[REQ-WP-074]]; one
  control per view.
- **Live exchange access in CI**: violates [[REQ-INFRA-002]]; tests use fake
  transports.

## What is still open

- **Exact subscription message format** for Bybit V5 and OKX v5: the plan
  records the documented shapes; the implementation will pin them byte-for-byte
  against the venues' docs. §46's references are the authority.
- **Connect rate limits**: `VenuePolicy.min_connect_interval_ns` is
  conservative; the true limits are unknown (establishing them means
  deliberately exceeding a venue's cap).
- **Reconnect backoff**: policy has `min_connect_interval_ns`; exponential
  backoff with cap is a planning choice.
- **Symbol mapping (§17)**: not in scope; a misconfigured symbol surfaces as
  the silence report.