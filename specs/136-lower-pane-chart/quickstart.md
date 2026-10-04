# Quickstart: validating the pane chart

1. `make web-test` (pure alignment, the mocked-library tests, FlowPane, Chart's handle) and `make test` (artifacts).
2. Rebuild `web`; open `/chart/binance/BTCUSDT?tf=15m`: Volume is a bar chart under the candles on the same axis; pan
   the main chart and the pane follows; hover a candle and the crosshair appears in the pane.
3. Choose CVD (base): one line per run, a zero line, a title and last value.
4. `PLAYWRIGHT_DIR=<dir> node specs/136-lower-pane-chart/screenshots.mjs`; look at all of them.
