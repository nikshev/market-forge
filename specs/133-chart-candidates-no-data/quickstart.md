# Quickstart: validating the feature

Prerequisites: `make web-install`; the dev stack up for the live check (`make up`); the web container rebuilt
(`docker compose up -d --build --no-deps web`).

1. **Tests**: `make web-test` (vitest: `extremumMarkers`, `panes`, `FlowPane`, `CandidateSwitch`, `Chart`
   with the library mocked) and `make test` (the artifact test).
2. **By eye**: open `/chart/binance/BTCUSDT?tf=15m`.
   - The chart shows green confirmed arrows and **no** grey "?" arrows. Press "Candidate extrema": grey arrows
     appear. Reload: they are gone.
   - The pane row shows the nine panes; while the features table has no producer, every one reads "no data"
     and none can be pressed; the region below says "No pane has data for this view".
3. **Screenshots**: `PLAYWRIGHT_DIR=<dir> node specs/133-chart-candidates-no-data/screenshots.mjs` writes the
   candidate (off/on) and pane-row shots, light and dark, to `docs/ui/`; look at each.
4. **Gate**: `make lint typecheck test web-typecheck web-test web-build` and `make graph && make validate`.
