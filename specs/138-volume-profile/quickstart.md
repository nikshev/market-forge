# Quickstart: validating the volume profile

1. `make test` and `make web-test`.
2. After the ingest is redeployed, wait for blocks: `curl '<api>/api/v1/volume-profile?venue=binance&symbol=BTCUSDT&window=24h'` returns bins and a
   coverage that grows with time.
3. Open `/chart/binance/BTCUSDT?tf=15m`: horizontal buy/sell bars at the side on the price levels; pan and zoom and they stay on their levels.
4. `PLAYWRIGHT_DIR=<dir> node specs/138-volume-profile/screenshots.mjs`; look at both.
