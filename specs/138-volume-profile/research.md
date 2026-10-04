# Research: the volume profile

## R1. Why not from bars
A bar has the aggressor split for the whole bar and no price inside it; PRD §14.1 requires trade-based bins and forbids inferring direction from anything else.

## R2. Why 5-minute blocks
Per-trade is too many rows; per-minute-per-tick is about fifty million rows a year per symbol; a 4h+ profile loses nothing at five minutes.

## R3. How to draw it
Series primitives (4.2.3) draw on the chart's canvas with the series' own price-to-coordinate, redrawn as the chart is.

## R4. Completeness
Binance ids are sequential per symbol (measured for the flow features, REQ-WP-088), so an id span that is not the trade count shows missed trades in a block.
