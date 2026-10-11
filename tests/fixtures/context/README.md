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
