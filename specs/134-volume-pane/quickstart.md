# Quickstart: validating the volume pane

1. `make web-test` (vitest: `volumeSeries`, availability, `FlowPane`, `App`) and `make test` (artifact test).
2. Rebuild `web` (`docker compose up -d --build --no-deps web`) and open `/chart/binance/BTCUSDT?tf=15m`: the
   pane row starts with Volume, selected, drawing one bar per candle; the other panes read "no data".
3. `PLAYWRIGHT_DIR=<dir> node specs/134-volume-pane/screenshots.mjs` writes the live screenshots, light and dark,
   to `docs/ui/`; look at both.
4. `make lint typecheck test web-typecheck web-test web-build`, then `make graph` and the trace `validate`.
