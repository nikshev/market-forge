# Quickstart: validating gap marking

1. `make web-test` and `make test`.
2. Rebuild `web`; open `/chart/binance/ETHUSDT?tf=1h`: an amber marker "148 missing" at the first bar after the hole and
   a notice under the chart naming it with its span; BTCUSDT 15m shows its own.
3. `PLAYWRIGHT_DIR=<dir> node specs/137-bar-gaps/screenshots.mjs`; look at all four.
