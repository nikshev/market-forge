---
id: REQ-API-001
title: Read API for bars, channel snapshots, signals and live updates
type: work-package
prd_ref: "§28 API Specification"
prd_lines: "4461-4545"
phase: null
status: draft
depends_on: ["REQ-WP-005", "REQ-WP-006", "REQ-WP-007"]
tags: []
hard_gated: false
---

## Requirement

PRD §28 specifies the read API the web UI consumes.

- `GET /api/v1/markets` — filters: venue, market_type, quote, active,
  min_volume.
- `GET /api/v1/bars` — params: venue, symbol, timeframe, start, end, limit.
- `GET /api/v1/channels` — params include `model`, and **historical
  `as_seen_then=true` default**.
- `GET /api/v1/features/snapshot` and `GET /api/v1/features/timeseries`.
- `GET /api/v1/signals` — filters: symbol, timeframe, setup_type, min_score,
  status, time range.
- `GET /api/v1/signals/{id}` — returns the decision snapshot, channel
  snapshot, feature snapshot, explanation, and **later outcome separately**.
- WebSocket `/ws/market`, subscribed with:

```json
{
  "op": "subscribe",
  "venue": "binance",
  "symbol": "BTCUSDT",
  "timeframe": "15m",
  "channels": ["bars", "channel", "features", "signals"]
}
```

§27.5 governs the channel endpoint's default: `AS-SEEN-THEN` is the immutable
channel snapshot at the selected time, `CURRENT REFIT` is the channel
calculated now over current history, and the deep-link default is
`AS-SEEN-THEN`.

## Acceptance

- bars are served for a venue, symbol and timeframe over a time range;
- channel snapshots are served, and `as_seen_then` defaults to true;
- a request for `as_seen_then=true` returns the snapshot as it was stored, not
  a refit;
- signals are served with the documented filters;
- a signal's detail returns its decision, channel and feature snapshots, and
  returns any later outcome as a separate field;
- a WebSocket subscription accepts the documented message and delivers updates
  on the channels it names.

## Trace

<!-- trace:begin -->
- **Outcomes:** [[OUT-2026-09-08-requirement-read-api]]
<!-- trace:end -->

## Notes

Hand-written rather than produced by `tools/extract_prd.py`: the extractor
walks the work-package and phase lists, and PRD §28 is a specification section
that no work package names. REQ-WP-009's chart cannot exist without it, which
is what surfaced the omission.

`min_score` and `setup_type` in §28.5, and the `score breakdown` and `model
probabilities` of §28.6's explanation, have no source yet — the ranker is PRD
§43 and the model is forbidden by Principle IV until baselines pass. Those
filters and fields are part of this requirement's PRD text and are not part of
its first implementation; see the spec's assumptions.
