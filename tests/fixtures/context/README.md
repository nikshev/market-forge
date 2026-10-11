# Recorded responses for the context collector (REQ-WP-093 to REQ-WP-096)

Recorded 2026-10-11 from this host, anonymously, with `curl`; the websocket frames with `websockets`
(`ws_*.json`, added with specs 146 and 147). Nothing here is edited by hand; a test that needs a different
value overrides a field in code and says so.

| File | URL |
|---|---|
| `binance_premiumIndex.json` | `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT` |
| `binance_openInterestHist.json` | `https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=5m&limit=3` |
| `binance_fundingRate.json` | `https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=30` |
| `bybit_tickers.json` | `https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT` |
| `bybit_funding_history.json` | `https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=30` |
| `bybit_instruments.json` | `https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT` |
| `okx_open_interest.json` | `https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP` |
| `okx_funding_rate.json` | `https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP` |
| `okx_mark_price.json` | `https://www.okx.com/api/v5/public/mark-price?instId=BTC-USDT-SWAP` |
| `okx_index_tickers.json` | `https://www.okx.com/api/v5/market/index-tickers?instId=BTC-USDT` |
| `okx_funding_history.json` | `https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=30` |
| `okx_instruments.json` | `https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP` |

## Websocket frames (REQ-WP-094, REQ-WP-095)

Recorded with `websockets` on the same day. Binance's futures streams moved to new paths in 2026: the
legacy `/ws/` path no longer delivers `forceOrder`, and `/market/ws/` (liquidations, mark price) and
`/public/ws/` (depth) do.

| File | Stream |
|---|---|
| `ws_okx_liquidation.json` | `wss://ws.okx.com:8443/ws/v5/public`, channel `liquidation-orders`, instType `SWAP` (three events, MAGIC-USDT-SWAP) |
| `ws_bybit_allLiquidation.json` | `wss://stream.bybit.com/v5/public/linear`, `allLiquidation.BTCUSDT` -- **only the subscription acknowledgement**: no liquidation arrived in four minutes, nor in ten across eight symbols |
| `ws3_binance_market_forceOrder_all.json` | `wss://fstream.binance.com/market/ws/!forceOrder@arr` (four events) |

| File | Stream |
|---|---|
| `ws4_okx_books.json` | OKX `books` channel for `BTC-USDT-SWAP`: the subscription ack, a 400-level snapshot, four updates (sizes are **contracts**) |
| `ws4_bybit_orderbook50.json` | Bybit `orderbook.50.BTCUSDT`: a snapshot, four deltas, and the subscription ack |
| `ws4_binance_spot_depth10_combined.json` | Binance spot `btcusdt@depth10@1000ms` and `ethusdt@depth10@1000ms` on the combined stream (`{"stream", "data"}`) -- whole top-ten snapshots, no timestamp |
| `ws5_okx_books_spot.json` | OKX `books` channel for the SPOT instruments `BTC-USDT` and `ETH-USDT`: acks, 400-level snapshots and updates -- sizes are **base units** (compare `ws4_okx_books.json`, a swap, whose sizes are contracts) |
