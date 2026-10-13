---
traces: [REQ-WP-106]
status: draft
---

# Feature Specification: Live windows on every timeframe

**Input**: [[REQ-WP-106]] -- owner's direction 2026-10-13. Builds on [[REQ-WP-102]].

## Scenarios

1. **Given** a 4h chart and live minutes, **Then** the last candle is the current 4h window and its close is the latest minute's price.
2. **Given** a closed 4h window the resampler has not stored, **Then** it is drawn, and called final only if all 240 minutes are there and final.
3. **Given** the feed is down, **Then** the window is built from the stored minutes and the chip says delayed.
4. **Given** the 1m chart, **Then** nothing extra is requested.
