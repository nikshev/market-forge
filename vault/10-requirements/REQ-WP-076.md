---
id: REQ-WP-076
title: The ingest daemon runs for Bybit and OKX, not only Binance
type: work-package
prd_ref: "§5.2, §6.2"
prd_lines: "315-319, 405-420"
phase: null
status: implemented
depends_on: [REQ-WP-066]
tags: []
---

## Requirement

§5.2 names the Phase 2 universe, verbatim:

> - Top 20–50 liquid Binance USDⓈ-M perpetuals;
> - Bybit linear perps;
> - OKX swaps.

§6.2's MVP compose list names one ingest service, `ingest-binance` — one per
venue, by its shape. Phase 2 therefore adds services rather than parameters to
the existing one.

### Most of this venue's work is already done, and none of it is wired

The normalisation layer exists for all three and is under test:
`src/channelflow/connectors/bybit/normalize.py`,
`.../okx/normalize.py`, each with its own suite. `VenuePolicy` likewise names
`BINANCE`, `BYBIT` and `OKX` (`src/channelflow/connectors/session.py`).

The live path does not. There is exactly one stream-URL builder,
`binance_stream_url` (`src/channelflow/connectors/websocket.py`); `streams_for`
builds names in Binance's own notation, `f"{symbol.lower()}@aggTrade"`; and
`build_daemon` (`src/channelflow/pipeline/ingest_main.py`) passes `BINANCE` and
the module-level `VENUE` as constants. So the daemon is not venue-agnostic code
waiting for configuration — it is Binance code, and this requirement is what
makes the venue a value.

§46's reference list names the two venues' own documentation — Bybit V5's
orderbook WebSocket and OKX's v5 API — which is where each venue's stream naming
and connection rules come from. They are not assumed to match Binance's.

## Acceptance

- A daemon runs for a venue named in **configuration**, with no venue constant
  left in the wiring path. Proven by starting one for Bybit and one for OKX from
  configuration alone.
- Each venue's stream names are built by that venue's own rule and pinned by a
  test against the names its documentation gives. Binance's `@aggTrade` notation
  is not assumed to generalise.
- Bars from each venue land with that venue's own value in the `venue` column, so
  §29.4's `(venue, symbol, timeframe, open_time)` ordering separates them.
- Raw frames archive under a prefix naming their venue, so one venue's archive
  cannot be read as another's.
- Each venue's connection obeys its own `VenuePolicy` — ping, pong and reconnect
  — rather than Binance's.
- A venue that connects and delivers nothing is **visible**: the condition is
  reported rather than appearing as a symbol that simply has no bars. An
  upper-case stream name on Binance's combined stream already produced exactly
  that silence once, and it was found by measurement rather than by a message.
- One process per symbol per venue, as [[REQ-WP-066]] established, with the same
  refusal when configuration names more.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-121-multi-venue-ingest]]
- **Tests:**
    - `tests/unit/connectors/test_binance_connector.py::TestBinanceConnector::test_close_delegates_to_transport`
    - `tests/unit/connectors/test_binance_connector.py::TestBinanceConnector::test_connect_calls_transport_with_correct_url`
    - `tests/unit/connectors/test_binance_connector.py::TestBinanceConnector::test_frames_delegates_to_transport`
    - `tests/unit/connectors/test_binance_connector.py::TestBinanceConnector::test_pong_delegates_to_transport`
    - `tests/unit/connectors/test_binance_connector.py::TestBinanceConnector::test_send_delegates_to_transport`
    - `tests/unit/connectors/test_bybit_connector.py::TestBybitConnector::test_close_closes_ws`
    - `tests/unit/connectors/test_bybit_connector.py::TestBybitConnector::test_connect_sends_subscribe_message`
    - `tests/unit/connectors/test_bybit_connector.py::TestBybitConnector::test_frames_delegates_to_internal_queue`
    - `tests/unit/connectors/test_bybit_connector.py::TestBybitConnector::test_pong_noop`
    - `tests/unit/connectors/test_bybit_connector.py::TestBybitConnector::test_send_delegates_to_ws`
    - `tests/unit/connectors/test_bybit_connector.py::TestBybitConnector::test_subscribe_message_format`
    - `tests/unit/connectors/test_okx_connector.py::TestOkxConnector::test_close_closes_ws`
    - `tests/unit/connectors/test_okx_connector.py::TestOkxConnector::test_connect_sends_subscribe_message`
    - `tests/unit/connectors/test_okx_connector.py::TestOkxConnector::test_pong_sends_bare_ping`
    - `tests/unit/connectors/test_okx_connector.py::TestOkxConnector::test_subscribe_message_format`
    - `tests/unit/connectors/test_venue_connector.py::TestStreamBuilders::test_binance_streams`
    - `tests/unit/connectors/test_venue_connector.py::TestStreamBuilders::test_bybit_streams`
    - `tests/unit/connectors/test_venue_connector.py::TestStreamBuilders::test_okx_streams`
    - `tests/unit/connectors/test_venue_connector.py::TestStreamBuilders::test_stream_builders_return_tuples`
    - `tests/unit/connectors/test_venue_connector.py::TestSubscribeMessages::test_binance_subscribe_message_returns_none`
    - `tests/unit/connectors/test_venue_connector.py::TestSubscribeMessages::test_bybit_subscribe_message_format`
    - `tests/unit/connectors/test_venue_connector.py::TestSubscribeMessages::test_okx_subscribe_message_format`
    - `tests/unit/connectors/test_venue_connector.py::TestUnknownVenue::test_unknown_venue_not_in_registry`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueConnectorProtocol::test_fake_implementation_satisfies_protocol`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueConnectorProtocol::test_protocol_has_required_methods`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_all_policies_have_min_connect_interval`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_binance_policy`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_bybit_policy`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_okx_policy`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueRegistry::test_binance_config`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueRegistry::test_bybit_config`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueRegistry::test_each_venue_has_required_fields`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueRegistry::test_okx_config`
    - `tests/unit/connectors/test_venue_connector.py::TestVenueRegistry::test_registry_contains_three_venues`
    - `tests/unit/connectors/test_websocket_builders.py::TestStreamBuilders::test_binance_streams`
    - `tests/unit/connectors/test_websocket_builders.py::TestStreamBuilders::test_bybit_streams`
    - `tests/unit/connectors/test_websocket_builders.py::TestStreamBuilders::test_okx_streams`
    - `tests/unit/connectors/test_websocket_builders.py::TestStreamBuilders::test_stream_builders_return_tuples`
    - `tests/unit/connectors/test_websocket_builders.py::TestSubscribeMessages::test_binance_subscribe_message_returns_none`
    - `tests/unit/connectors/test_websocket_builders.py::TestSubscribeMessages::test_bybit_subscribe_message_format`
    - `tests/unit/connectors/test_websocket_builders.py::TestSubscribeMessages::test_no_builder_is_another_with_string_replaced`
    - `tests/unit/connectors/test_websocket_builders.py::TestSubscribeMessages::test_okx_subscribe_message_format`
    - `tests/unit/deploy/test_compose_names.py::test_a_comment_mentioning_an_address_is_not_a_finding`
    - `tests/unit/deploy/test_compose_names.py::test_loopback_and_the_any_address_are_not_findings`
    - `tests/unit/deploy/test_compose_names.py::test_the_check_sees_the_address_it_exists_to_catch`
    - `tests/unit/deploy/test_compose_names.py::test_the_compose_file_names_no_container_by_address`
    - `tests/unit/pipeline/test_archive_prefix.py::TestFrameArchivePrefix::test_binance_venue_prefix`
    - `tests/unit/pipeline/test_archive_prefix.py::TestFrameArchivePrefix::test_bybit_venue_prefix`
    - `tests/unit/pipeline/test_archive_prefix.py::TestFrameArchivePrefix::test_okx_venue_prefix`
    - `tests/unit/pipeline/test_ingest.py::test_registry_connector_paths_resolve_to_importable_classes`
    - `tests/unit/pipeline/test_ingest_daemon.py::TestIngestDaemonWithVenue::test_archive_prefix_contains_venue`
    - `tests/unit/pipeline/test_ingest_daemon.py::TestIngestDaemonWithVenue::test_daemon_connect_called_with_correct_streams`
    - `tests/unit/pipeline/test_ingest_daemon.py::TestIngestDaemonWithVenue::test_daemon_venue_attribute`
    - `tests/unit/pipeline/test_ingest_session.py::TestStreamSessionWithVenueConnector::test_session_accepts_fake_connector`
    - `tests/unit/pipeline/test_ingest_session.py::TestStreamSessionWithVenueConnector::test_session_calls_connect_on_start`
    - `tests/unit/pipeline/test_ingest_session.py::TestStreamSessionWithVenueConnector::test_session_close_delegates_to_connector`
    - `tests/unit/pipeline/test_ingest_session.py::TestStreamSessionWithVenueConnector::test_session_reads_frames_from_connector`
    - `tests/unit/pipeline/test_silence_detector.py::test_a_frame_arriving_resets_the_silence_timer`
    - `tests/unit/pipeline/test_silence_detector.py::test_a_silent_connection_is_reported_with_the_venue_and_reconnected`
    - `tests/unit/pipeline/test_stream_session_policies.py::TestStreamSessionPolicies::test_binance_policy_uses_websocket_ping`
    - `tests/unit/pipeline/test_stream_session_policies.py::TestStreamSessionPolicies::test_bybit_policy_pings_with_payload`
    - `tests/unit/pipeline/test_stream_session_policies.py::TestStreamSessionPolicies::test_bybit_reconnects_on_silence_no_close_frame`
    - `tests/unit/pipeline/test_stream_session_policies.py::TestStreamSessionPolicies::test_okx_policy_pings_bare_string`
    - `tests/unit/pipeline/test_stream_session_policies.py::TestStreamSessionPolicies::test_okx_reconnects_on_close_frame`
- **Code:**
    - `src/channelflow/connectors/__init__.py`
    - `src/channelflow/connectors/binance/__init__.py`
    - `src/channelflow/connectors/binance/connector.py`
    - `src/channelflow/connectors/bybit/__init__.py`
    - `src/channelflow/connectors/bybit/connector.py`
    - `src/channelflow/connectors/okx/__init__.py`
    - `src/channelflow/connectors/okx/connector.py`
    - `src/channelflow/connectors/venue.py`
    - `src/channelflow/pipeline/ingest.py`
    - `src/channelflow/pipeline/ingest_main.py`
    - `src/channelflow/pipeline/venue_normalize.py`
- **Outcomes:** [[OUT-2026-09-23-plan-multi-venue-ingest]], [[OUT-2026-09-23-spec-multi-venue-ingest]], [[OUT-2026-09-23-tasks-multi-venue-ingest]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

### 2026-10-02: six days after `implemented`, the deployment it was written for did not work

This requirement is `implemented`, every test it names is green, and the OKX connector never
delivered a frame, a Binance connection that ended was never reopened, and the raw archive was
filed in the wrong place. Recorded here rather than by moving the status, for the reason
[[REQ-PHASE-1]]'s 2026-09-17 note gives: the code did what its tests said, and the tests asked
the wrong questions (a fake whose `send` always worked, a silence limit read from a field that
held something else, an archive tested with its default prefix and never through the wiring).
[[REQ-WP-078]] closes each of them and carries the measurements.
