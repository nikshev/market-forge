# Quickstart: validating CVD from bars

1. `make test` (the function, breaks, the sink, the worker wiring, the registry) and `make web-test` (the line break).
2. Measure SC-005: for live Binance bars, the share with `last_trade_id − first_trade_id + 1 == trade_count`.
3. After a worker pass: `curl '<api>/api/v1/features/timeseries?venue=binance&symbol=BTCUSDT&timeframe_ns=900000000000&start_ns=...&end_ns=...'`
   returns `cvd_base` in `values`; the BTCUSDT 15m chart's "CVD (base)" pane draws it.
4. `PLAYWRIGHT_DIR=<dir> node specs/135-trade-flow-features/screenshots.mjs` writes the live pane, light and dark.
