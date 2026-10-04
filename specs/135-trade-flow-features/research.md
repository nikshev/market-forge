# Research: CVD from bars

## R1. Where the aggressor split already is
**Finding**: `Bar`/the bars table carry `aggressive_buy_base`, `aggressive_sell_base`, `delta_base`, `trade_count`,
`first_trade_id`, `last_trade_id`; `resample.fold` sums them over complete windows. **Decision**: derive from bars.

## R2. Notional versus base
**Finding**: PRD §15.4 and `FlowTracker` use notional; the bar stores base-unit sides and a quote total. **Decision**:
base units under `*_base` names, an ADR, and the way back (store the quote split, register notional).

## R3. Continuity
**Finding**: a missing bar is a gap in `open_time_ns`; Binance `aggTrade` ids are sequential so a jump or an id-span
mismatch shows a missed trade; Bybit/OKX ids are not guaranteed sequential. **Decision**: runs (D3), the limit stated.

## R4. Where it runs
**Finding**: the worker reads every series' bars each pass. **Decision**: the flow step goes there.
