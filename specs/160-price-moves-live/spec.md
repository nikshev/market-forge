---
traces: [REQ-WP-108]
status: draft
---

# Feature Specification: The price moves on the last bar

**Input**: [[REQ-WP-108]] -- owner's direction 2026-10-13 ("on Investing the price moves on the last bar; here it does not"). Builds on
[[REQ-WP-102]] and [[REQ-WP-106]].

## Scenarios

1. **Given** the live feed is up, **Then** the last candle's close and the price label change several times a second while the market moves.
2. **Given** the API restarts, **Then** the cache is rebuilt from the finals replayed from the final topic, and none of that replay reaches a browser.
3. **Given** a forming bar unchanged since the last publish, **Then** it is not published again.
4. **Given** a chart opens, **Then** the newest bar is clear of the volume profile and wide enough to see move; **given** the reader has scrolled
   back, **Then** a new bar does not pull the view away.
