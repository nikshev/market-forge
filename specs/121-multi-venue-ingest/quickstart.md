# Quickstart: proving multi-venue ingest works

## Prerequisites

- `make install`
- `make up` (stack up, ingest-binance already running)
- `.env` has `CHANNELFLOW_INGEST_SYMBOLS_BYBIT` and `CHANNELFLOW_INGEST_SYMBOLS_OKX` set.

## 1. The suite

```sh
make test-fast
```

All backend tests pass (no live exchange access needed). The fake transport tests in `tests/unit/connectors/` exercise each venue's connector.

## 2. The suite (web)

```sh
cd apps/web && npx vitest run
```

No frontend changes for this feature.

## 3. Against the running stack

**Before**: only `ingest-binance` runs; `bars` has only `binance` rows.

**Start the new services**:

```sh
docker compose up -d --build ingest-bybit ingest-okx
```

**Wait for healthy** (the services log their connection/subscription):

```sh
docker compose logs -f ingest-bybit ingest-okx
```

Look for:
```
bybit: connected to wss://stream.bybit.com/v5/public/linear
bybit: subscribed to publicTrade.BTCUSDT
okx: connected to wss://ws.okx.com:8443/api/v5/market
okx: subscribed to trades.BTC-USDT-SWAP
```

**After a minute**, check the API:

```sh
curl -s localhost:8000/api/v1/bars?venue=bybit&symbol=BTCUSDT&timeframe_ns=60000000000
curl -s localhost:8000/api/v1/bars?venue=okx&symbol=BTC-USDT-SWAP&timeframe_ns=60000000000
```

Expect non-empty `bars` arrays with `venue` equal to `bybit` and `okx` respectively.

**Archive check** (MinIO console or `mc`):

```
mc ls minio/channelflow-dev/bybit/raw/cex/
mc ls minio/channelflow-dev/okx/raw/cex/
```

Should show archive objects under `bybit/raw/cex/` and `okx/raw/cex/`.

**Silence test** (optional, manual):

```sh
# Configure a symbol that doesn't exist on the venue
# CHANNELFLOW_INGEST_SYMBOLS_BYBIT=INVALID_SYMBOL
# docker compose restart ingest-bybit
# Watch logs: should see "silence detected" with venue=bybit, symbol=INVALID_SYMBOL
```

## 4. What is still out of reach

- **Symbol mapping** (§17): a symbol typed wrong (e.g., `BTCUSDT` on OKX instead of `BTC-USDT-SWAP`) will surface as a silence report, not a guessed translation.
- **Cross-venue arbitrage signals** (§17): needs cross-venue symbol registry; separate requirement.
- **Historical backfill**: the daemon only ingests live; backfill is a separate replay.