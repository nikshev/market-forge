---
id: REQ-API-001
title: Read API for bars, channel snapshots, signals and live updates
type: work-package
prd_ref: "§28 API Specification"
prd_lines: "4461-4545"
phase: null
status: planned
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

- markets are served, filterable by venue and market type;
- bars are served for a venue, symbol and timeframe over a time range;
- channel snapshots are served, and `as_seen_then` defaults to true;
- a request for `as_seen_then=true` returns the snapshot as it was stored, not
  a refit;
- a feature snapshot is served for a venue, symbol, timeframe and time, and a
  feature time series over a range;
- signals are served with the documented filters;
- a signal's detail returns its decision, channel and feature snapshots, and
  returns any later outcome as a separate field;
- a WebSocket subscription accepts the documented message and delivers updates
  on the channels it names.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-013-chart-and-read-api]]
- **Tests:**
    - `tests/unit/api/test_channel_modes.py::test_a_refit_without_enough_history_is_refused`
    - `tests/unit/api/test_channel_modes.py::test_a_snapshot_taken_after_the_instant_is_not_returned`
    - `tests/unit/api/test_channel_modes.py::test_as_seen_then_is_never_reconstructed_after_the_fact`
    - `tests/unit/api/test_channel_modes.py::test_as_seen_then_returns_the_stored_snapshot_unchanged`
    - `tests/unit/api/test_channel_modes.py::test_the_parameter_defaults_to_as_seen_then`
    - `tests/unit/api/test_channel_modes.py::test_the_refit_cannot_see_past_the_requested_instant`
    - `tests/unit/api/test_channel_modes.py::test_the_two_modes_disagree_and_that_is_the_point`
    - `tests/unit/api/test_reads.py::test_a_feature_snapshot_is_served`
    - `tests/unit/api/test_reads.py::test_a_feature_time_series_is_served`
    - `tests/unit/api/test_reads.py::test_a_limit_returns_the_most_recent_bars`
    - `tests/unit/api/test_reads.py::test_a_signal_detail_separates_the_later_outcome`
    - `tests/unit/api/test_reads.py::test_an_unknown_signal_is_a_not_found`
    - `tests/unit/api/test_reads.py::test_an_unknown_symbol_returns_an_empty_result`
    - `tests/unit/api/test_reads.py::test_bars_are_served_in_event_time_order`
    - `tests/unit/api/test_reads.py::test_bars_honour_the_time_range`
    - `tests/unit/api/test_reads.py::test_markets_are_served`
    - `tests/unit/api/test_reads.py::test_markets_filter_by_market_type`
    - `tests/unit/api/test_reads.py::test_markets_filter_by_venue`
    - `tests/unit/api/test_reads.py::test_signals_are_served_and_filtered`
    - `tests/unit/api/test_reads.py::test_signals_filter_by_time_range`
    - `tests/unit/api/test_ws.py::test_a_malformed_message_is_answered_not_fatal[not json at all-not JSON]`
    - `tests/unit/api/test_ws.py::test_a_malformed_message_is_answered_not_fatal[{"op": "subscribe", "venue": "b", "symbol": "s", "timeframe": "1m", "channels": ["bras"]}-unknown channel]`
    - `tests/unit/api/test_ws.py::test_a_malformed_message_is_answered_not_fatal[{"op": "subscribe", "venue": "b", "symbol": "s", "timeframe": "1m", "channels": []}-non-empty list]`
    - `tests/unit/api/test_ws.py::test_a_malformed_message_is_answered_not_fatal[{"op": "subscribe", "venue": "binance"}-missing field]`
    - `tests/unit/api/test_ws.py::test_a_malformed_message_is_answered_not_fatal[{"op": "unsubscribe"}-unsupported op]`
    - `tests/unit/api/test_ws.py::test_a_published_update_reaches_the_subscriber`
    - `tests/unit/api/test_ws.py::test_an_update_nobody_subscribed_to_reaches_nobody`
    - `tests/unit/api/test_ws.py::test_another_symbol_is_not_delivered`
    - `tests/unit/api/test_ws.py::test_only_subscribed_channels_are_delivered`
    - `tests/unit/api/test_ws.py::test_the_documented_subscribe_message_is_accepted`
- **Code:**
    - `src/channelflow/api/__init__.py`
    - `src/channelflow/api/app.py`
    - `src/channelflow/api/channels.py`
    - `src/channelflow/api/repositories.py`
    - `src/channelflow/api/routes.py`
    - `src/channelflow/api/schemas.py`
    - `src/channelflow/api/ws.py`
- **Outcomes:** [[OUT-2026-09-08-plan-chart-and-read-api]], [[OUT-2026-09-08-requirement-read-api]], [[OUT-2026-09-08-spec-chart-and-read-api]], [[OUT-2026-09-08-tasks-chart-and-read-api]]
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
