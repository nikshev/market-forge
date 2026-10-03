# Research: markets registered

## R1. Who writes the markets table in the running stack?
Nobody. `LakehouseRepository.add_market` and `features.market_row` exist; a search of `src/` shows no caller
outside tests. `GET /api/v1/markets` answers `{"markets":[]}`.

## R2. What market type is each daemon's feed?
Binance: `wss://stream.binance.com:9443/stream?streams=…` (`websocket.binance_stream_url`) — spot.
Bybit: `wss://stream.bybit.com/v5/public/linear` — linear perpetuals. OKX: v5 public, the instrument decides;
the configured one is `BTC-USDT-SWAP`, a perpetual. PRD §26.1's example says "Binance Perp"; it does not
describe this deployment.

## R3. Is a constant per venue enough?
For Binance and Bybit, yes. For OKX only while the instrument is a swap. **Decision:** a function of the
symbol, refusing an unrecognised form.

## R4. Where does the no-rules row live?
Inline in `LakehouseRepository.add_market` (API layer). Ingest cannot import the API. **Decision:** build it in
`tables/features.py` and have `add_market` use it.

## R5. What happens when five daemons start together?
Each appends its own key. Iceberg retries a conflicting commit ([[REQ-WP-039]]); the latest-row-per-key read
makes a duplicate harmless. Tested on SQLite and on the stack's PostgreSQL.

## R6. What does the page need?
Nothing: it renders `symbol` as a chart link, `venue · market_type`, and absent scores.
