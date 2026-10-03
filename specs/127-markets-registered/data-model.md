# Data Model: markets registered

No schema change. A registered market is a row of `markets`:

| column | value |
|---|---|
| venue, symbol | the daemon's |
| market_type | `VENUE_REGISTRY[venue].market_type(symbol)` |
| base_asset, quote_asset, contract_size, status | empty strings |
| tick_size, step_size, min_notional | 0 (read back as "no rules": `instrument_from_row` returns nothing) |

`market_type(symbol)` per venue: binance → `spot`; bybit → `perp`; okx → `perp` for `…-SWAP`, `spot` for a
two-part `BASE-QUOTE`, otherwise `ValueError`.
