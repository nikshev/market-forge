---
id: REQ-WP-078
title: The multi-venue ingest stays connected, files its archive where readers look, and keeps its log bounded
type: work-package
prd_ref: "§6.2, §6.4.4, §32, §33, §35.6"
prd_lines: "405-420, 600-642, 4752-4781, 4783-4799, 4897-4905"
phase: null
status: implemented
depends_on: [REQ-WP-076]
tags: [ingest, reliability]
---

## Requirement

[[REQ-WP-076]] is `implemented`, its tests are green, and on 2026-10-02 — six
days after it landed — the deployment it was written for looked like this:

| venue / symbol | state | evidence |
|---|---|---|
| Bybit BTCUSDT | working | newest 1m bar at 10:35, 8,743 bars |
| Binance BTCUSDT | **dead since 09-28 07:45**, container `Up` | silence of 356,633 s logged five times a second; nothing reconnects |
| Binance ETHUSDT, SOLUSDT | crash-looping, 8,534 restarts | `failed to resolve host 'postgres'` (a network fault, repaired separately) |
| OKX BTC-USDT-SWAP | **never delivered a frame** | no row with `venue = 'okx'` in `bars`, ever |
| raw archive | **wrong place, and one symbol in three per minute** | see defect 4 |
| logs | 6.6 GB for one service in six days | INFO on every trade, frame and step |

This requirement is the repair. PRD §6.2 puts one ingest service per venue in
the deployment, §6.4.4 gives the raw zone its layout, §32 and §33 list the
health signals a feed owes the rest of the system — "WS reconnect count",
"stale seconds", "reconnects", "stale feed count" — and §35.6 names reconnect
among what connector tests must cover. None of those is met by a connector that
dies once and stays dead without saying so.

### Six defects, each measured

**1. OKX cannot connect, and says nothing.** The daemon opens
`wss://ws.okx.com/api/v5/market`. That is a REST path prefix, not a socket:
connecting to it returns `HTTP 404`. The connector's thread swallows the
exception, so the log holds only the silence detector's warnings. Even at the
right URL, `okx_streams` returns `trades.BTC-USDT-SWAP` and
`okx_subscribe_message` puts that whole string into `instId`; OKX answers
`Subscribe failed, wrong URL or channel:trades,instId:trades.BTC-USDT-SWAP
doesn't exist`. Verified live from the host against
`wss://ws.okx.com:8443/ws/v5/public`: with `instId = BTC-USDT-SWAP` trades
arrive immediately; with the prefix the venue rejects the subscription.

**2. A connection that ends is never reopened — for two venues of three.**
`StreamSession.tick` reconnects on silence only when `not
policy.announces_close`, which is true for Bybit alone. Binance and OKX are
assumed to send a close frame, and the connector classes do not turn one into a
reconnect: their reader thread ends on any exception or close and nothing
notices that it has. For Binance, `WebsocketTransport._run` catches the
exception, stores it in `_failure` and returns — and `_failure` is read only by
`connect()`, on the first connection, never afterwards. A Binance daemon whose
socket dies is therefore a container that is `Up`, has no feed, and reports
nothing but a warning.

**3. The silence limit is a different quantity from the one it borrows.**
`IngestDaemon._check_silence` takes `policy.idle_timeout_ns` and doubles it. For
Bybit and OKX that field is "how long the venue tolerates a silent *client*" —
a few tens of seconds. For Binance, `venue.py` sets it to 24 hours, and the
threshold is therefore 48 hours: a Binance feed that went silent at 09-28 07:45
could not have been reported before 09-30 07:45 at the earliest. A 24-hour figure is Binance's **stream
lifetime**. `connectors/session.py`'s own `BINANCE` policy has exactly that:
`stream_lifetime_ns=24 * 60 * 60 * SECOND_NS` and no idle timeout. The
[[REQ-WP-076]] copy in `connectors/venue.py` moved the value into the wrong
field and dropped the lifetime, so the 24-hour reconnect `tick` was written to
perform no longer happens. Two registries now define each venue's policy with
different numbers (OKX: 30 s in one, 30.9 s in the other), and the live daemon
uses the one with the mistake.

**4. The raw archive is filed twice over, and under a key with no symbol in it.** `build_daemon` passes
`prefix=f"{venue}/raw/cex"` and `FrameArchive.key_for` then appends
`self.venue` again, so a frame lands at
`binance/raw/cex/binance/2026/10/02/1059.jsonl.gz` — the bucket root, not
`raw/cex/`. Measured through the S3 API: `raw/cex/binance/` holds 12,850 objects
and **stops at 09-26 07:25**; `binance/raw/cex/binance/` holds 2,892 and
`bybit/raw/cex/bybit/` 8,837, both current. PRD §6.4.4 lays the zone out as
`s3://channel-flow/raw/cex/…`, and everything that reads the archive —
`tools/record/parity_capture.py` and the replay it feeds ([[REQ-NRT-PARITY]]) —
looks there. The existing test, `test_archive_prefix.py`, builds a
`FrameArchive` with its **default** prefix and checks `key_for`, so it passes
against a wiring that has never used that prefix: it tests the class and not
the seam where the mistake is.

**And the key names no symbol.** `key_for` is `<prefix>/<venue>/<date>/<HHMM>`:
venue and minute, nothing else. That was enough while one process wrote one
venue. The deployment runs three Binance processes — BTCUSDT, ETHUSDT, SOLUSDT,
one each because `ingest_main` refuses more than one symbol — and all three
write `…/HHMM.jsonl.gz`. `store.put` replaces an object, so the last process to
flush a minute wins and the other two symbols' frames for it are gone.
Measured by opening sampled objects and reading the `stream` of every frame in
them: `09/20 12:00` holds 467 frames, all `ethusdt@aggtrade`; `09/23 09:30`
holds 430, all `btcusdt@aggtrade`; `09/25 15:00` holds 235, all
`solusdt@aggtrade`; the three most recent minutes read on 10-02 were `sol`,
`eth`, `sol`. Object count says the same thing from the other side: with three
writers the archive grew by **one** object a minute.

This began on 2026-09-17, when `ingest-binance-eth` and `ingest-binance-sol` were
added to the compose file to meet §5.1's three symbols; nobody — including the
change that added them — asked whether the three shared a key space. Bars and
channels are unaffected, because they are built from the live stream and not read
back from the archive. The raw tier is what suffers, and it is the tier §7
calls the source of truth "where re-normalization may be required": frames
overwritten there cannot be recovered. Of the 12,850 minute-objects under
`raw/cex/binance/`, those written from the day ETH and SOL were added until the
archive moved on 09-26 each retain one symbol of three, chosen by timing; the
first couple of hours on 09-17, when BTC ran alone, are whole.

**5. The log carries debugging output at INFO.** Per trade, per frame and per
200 ms step: `BarBuilder.add called for trade …`, `_finalize_ready: …`,
`Normalized 1 trade(s)`, `Received raw frame: …`, `FrameArchive.flush called …
frames=0`, `S3ObjectStore.put succeeded`. Measured container log sizes after
six days: Bybit 6.6 GB, OKX 502 MB, Binance 177 MB — and the silence warning
repeats at 5 Hz for as long as the condition lasts. Compose sets no log
rotation, so none of it is bounded.

**6. A failed connection and a rejected subscription are invisible.** Items 1
and 2 are the same fault seen from two sides: a thread that ends without a word
cannot be told from a quiet market, which is the failure mode this repository
has recorded more than once and decided against each time.

### What this deliberately does not do

- **No new metrics.** §33 lists "reconnects" and "stale feed count", and
  `docs/deployment.md` already records that nine of §33's eleven metrics have no
  producer ([[REQ-WP-055]]). Giving these two a producer without a dashboard to
  say so would repeat that. Reconnects and silence become **log events with a
  stated reason**; turning them into metrics is left open and named.
- **No change to the DNS repair.** The lost network aliases on `postgres` and
  `minio` and the hard-coded container addresses were fixed on 2026-10-02
  (`1cf4edb`); they are the cause of the ETH and SOL crash loop, not of anything
  here.

## Acceptance

- **OKX connects.** The OKX connector opens `wss://ws.okx.com:8443/ws/v5/public`
  and subscribes with `instId` set to the instrument as OKX names it
  (`BTC-USDT-SWAP`), pinned by a test over what the connector is *built with*,
  not over a helper's return value. On a running deployment, a trade frame
  arrives and a bar is committed — checked by hand against the live venue and
  recorded in the implement outcome note, because CI has no network.
- **A rejection is a warning that quotes the venue.** An `"event":"error"` frame
  from a venue, and a connection that fails to open, each log at WARNING with
  the venue and the venue's own message. A reader thread never exits without a
  log line saying why.
- **A connection that ends is reopened, for every venue.** Whatever ended it — a
  close frame, an exception, or silence — `StreamSession` reconnects, subject to
  `min_connect_interval_ns`. Proven with a fake connector whose reader dies
  **without** a close frame and whose venue has `announces_close=True`: today's
  shape for Binance and OKX, and the one `tick` ignores.
- **Silence is measured against its own limit.** A policy carries a maximum
  silence that is not its idle timeout. It is configuration (Principle X), with
  a default per venue written in the policy and a stated basis for each. A
  feed silent past it is reconnected, and the log says so once on entry and once
  on recovery rather than on every step.
- **Binance's 24-hour lifetime is honoured again.** `stream_lifetime_ns` is set
  on Binance's policy and the session reconnects when it elapses — proven with a
  fake clock advanced past 24 hours.
- **One definition of a venue's policy.** The two registries are reduced to one;
  a test fails if a venue's policy is defined in two places with different
  values.
- **The archive key is right where it is built.** A test constructs the daemon
  through `build_daemon` with the deployment's own `CHANNELFLOW_ARCHIVE_URI` and
  asserts the key of a written frame has the venue **once**, under `raw/cex/`,
  and names the symbol. A test that cannot fail on the mistake above is not this
  criterion.
- **Two symbols of one venue never share an object.** Two archives for different
  symbols of the same venue, flushed in the same minute, produce two objects, each
  holding only its own symbol's frames. Proven by reading the frames back, not by
  comparing key strings: the earlier mistake looked fine as a string.
- **The loss is stated, not hidden.** The implement outcome note records, per
  symbol, how many already-written minute-objects hold that symbol, so the extent
  of what was overwritten between 2026-09-17 and 2026-09-26 is a number somebody
  can read.
- **The misplaced objects are moved, not abandoned.** Objects already written —
  under `<venue>/raw/cex/<venue>/` and the 12,850 under `raw/cex/binance/` —
  are placed under the new layout by the symbol their own frames name, verified
  equal by size and checksum, and only then removed from the old location. An
  object holding more than one symbol is refused and left where it is. The counts
  before and after are recorded in the implement outcome note.
- **The log is bounded.** Nothing on the per-trade, per-frame or per-step path
  logs at INFO. A repeated condition does not repeat its line. Every service in
  `docker-compose.yml` carries a log size cap, and a test reads the file to
  prove none is without one. Measured log bytes per minute for each ingest
  service before and after are recorded in the implement outcome note.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-123-ingest-resilience]]
- **Tests:**
    - `tests/unit/connectors/test_policies_single_home.py::test_each_venue_has_one_policy_across_the_connectors_package`
    - `tests/unit/connectors/test_policies_single_home.py::test_the_collector_sees_the_three_live_venues_and_hypercore`
    - `tests/unit/connectors/test_policies_single_home.py::test_the_guard_can_fail`
    - `tests/unit/connectors/test_reader_endings.py::test_a_close_from_the_venue_is_logged_with_its_code[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_close_from_the_venue_is_logged_with_its_code[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_failure_mid_stream_keeps_what_arrived_and_says_why[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_failure_mid_stream_keeps_what_arrived_and_says_why[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_new_connect_forgets_the_previous_socket_before_the_new_one_opens[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_new_connect_forgets_the_previous_socket_before_the_new_one_opens[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_reader_that_is_running_is_alive_and_a_close_we_asked_for_is_not_an_error[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_reader_that_is_running_is_alive_and_a_close_we_asked_for_is_not_an_error[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_refusal_is_queued_for_the_archive_and_warned_with_the_venues_words[bybit-BybitConnector-{"success": false, "ret_msg": "error:handler not found,topic:publicTrade.NOTASYMBOL", "conn_id": "x", "req_id": "", "op": "subscribe"}-handler not found]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_refusal_is_queued_for_the_archive_and_warned_with_the_venues_words[okx-OkxConnector-{"event": "error", "msg": "Subscribe failed, wrong URL or channel:trades,instId:trades.BTC-USDT-SWAP doesn't exist. Please use the correct URL, channel and parameters referring to API document.", "code": "60018", "connId": "b2b0944b"}-Subscribe failed]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_send_after_the_reader_ended_does_not_write_to_the_dead_socket[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_send_after_the_reader_ended_does_not_write_to_the_dead_socket[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_socket_that_will_not_open_is_a_warning_and_a_dead_reader[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_socket_that_will_not_open_is_a_warning_and_a_dead_reader[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_a_transport_that_was_never_connected_is_not_alive`
    - `tests/unit/connectors/test_reader_endings.py::test_alive_is_false_as_soon_as_a_stop_is_asked_for_not_when_the_reader_returns[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_alive_is_false_as_soon_as_a_stop_is_asked_for_not_when_the_reader_returns[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_an_old_reader_ending_does_not_forget_its_replacements_socket[bybit-BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_an_old_reader_ending_does_not_forget_its_replacements_socket[okx-OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_binances_transport_logs_a_failure_after_connect_and_stops_being_alive`
    - `tests/unit/connectors/test_reader_endings.py::test_every_real_connector_answers_whether_its_reader_is_running[BinanceConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_every_real_connector_answers_whether_its_reader_is_running[BybitConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_every_real_connector_answers_whether_its_reader_is_running[OkxConnector]`
    - `tests/unit/connectors/test_reader_endings.py::test_the_protocol_names_alive`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[binance-"a string"]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[binance-42]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[binance-[]]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[binance-]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[binance-not json at all]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[binance-null]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[bybit-"a string"]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[bybit-42]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[bybit-[]]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[bybit-]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[bybit-not json at all]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[bybit-null]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[okx-"a string"]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[okx-42]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[okx-[]]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[okx-]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[okx-not json at all]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_of_any_other_shape_is_none_and_never_raises[okx-null]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[binance-{"event":"error","msg":"Subscribe failed, wrong URL or channel:trades,instId:trades.BTC-USDT-SWAP doesn't exist. Please use the correct URL, channel and parameters referring to API document.","code":"60018","connId":"b2b0944b"}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[binance-{"stream": "btcusdt@aggTrade", "data": {}}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[bybit-{"success": true, "ret_msg": "", "op": "subscribe"}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[bybit-{"topic": "publicTrade.BTCUSDT", "data": []}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[okx-pong]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[okx-{"arg": {"channel": "trades"}, "data": [{"px": "1"}]}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[okx-{"event": "subscribe", "arg": {"channel": "trades", "instId": "X"}}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_a_frame_that_is_not_this_venues_refusal_is_none[okx-{"success":false,"ret_msg":"error:handler not found,topic:publicTrade.NOTASYMBOL","conn_id":"da7tne17jutmkv5im010-bcdap","req_id":"","op":"subscribe"}]`
    - `tests/unit/connectors/test_rejection_frames.py::test_an_unknown_venue_is_none`
    - `tests/unit/connectors/test_rejection_frames.py::test_bybit_refusal_returns_the_venues_message`
    - `tests/unit/connectors/test_rejection_frames.py::test_okx_refusal_returns_the_venues_message`
    - `tests/unit/connectors/test_session_policies.py::test_a_venue_that_announces_its_closes_is_still_reconnected_when_it_goes_quiet`
    - `tests/unit/connectors/test_silence_limit.py::test_a_venue_that_announces_close_and_names_no_limit_has_none`
    - `tests/unit/connectors/test_silence_limit.py::test_a_venue_that_gives_up_silently_falls_back_to_its_idle_timeout`
    - `tests/unit/connectors/test_silence_limit.py::test_an_explicit_limit_wins`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_binance_policy`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_bybit_policy`
    - `tests/unit/connectors/test_venue_connector.py::TestVenuePolicies::test_okx_policy`
    - `tests/unit/connectors/test_venue_policies_values.py::test_binance_has_a_lifetime_and_no_idle_timeout`
    - `tests/unit/connectors/test_venue_policies_values.py::test_bybit_pings_every_twenty_seconds_against_a_sixty_second_limit`
    - `tests/unit/connectors/test_venue_policies_values.py::test_each_live_venue_has_a_silence_limit_with_a_basis[binance]`
    - `tests/unit/connectors/test_venue_policies_values.py::test_each_live_venue_has_a_silence_limit_with_a_basis[bybit]`
    - `tests/unit/connectors/test_venue_policies_values.py::test_each_live_venue_has_a_silence_limit_with_a_basis[okx]`
    - `tests/unit/connectors/test_venue_policies_values.py::test_okx_pings_every_fifteen_seconds_against_a_thirty_second_limit`
    - `tests/unit/connectors/test_venue_policy_validation.py::test_a_silence_limit_longer_than_the_keepalive_is_accepted`
    - `tests/unit/connectors/test_venue_policy_validation.py::test_a_silence_limit_must_be_positive[-1]`
    - `tests/unit/connectors/test_venue_policy_validation.py::test_a_silence_limit_must_be_positive[0]`
    - `tests/unit/connectors/test_venue_policy_validation.py::test_a_silence_limit_shorter_than_the_keepalive_is_refused`
    - `tests/unit/connectors/test_venue_policy_validation.py::test_the_backoff_ceiling_cannot_be_below_the_minimum_interval`
    - `tests/unit/connectors/test_venue_policy_validation.py::test_the_default_ceiling_is_a_minute`
    - `tests/unit/deploy/test_compose_logging.py::test_every_ingest_service_is_handed_the_silence_limit_and_the_log_level`
    - `tests/unit/deploy/test_compose_logging.py::test_every_service_has_a_log_size_cap`
    - `tests/unit/deploy/test_compose_logging.py::test_the_cap_is_configuration_with_a_default_and_keeps_a_few_files`
    - `tests/unit/deploy/test_compose_logging.py::test_the_check_fails_for_a_service_without_one`
    - `tests/unit/parity/test_parity_capture_prefix.py::test_no_symbols_prefix_is_a_prefix_of_another_symbols_objects`
    - `tests/unit/parity/test_parity_capture_prefix.py::test_the_prefix_names_venue_and_symbol`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_copy_that_does_not_verify_leaves_the_source_and_removes_the_bad_copy`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_destination_holding_different_bytes_is_never_overwritten`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_destination_that_already_holds_the_same_bytes_lets_the_source_go`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_dry_run_changes_nothing_and_says_what_it_would_do`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_frame_names_its_symbol_in_the_configured_spelling[binance-{"stream": "btcusdt@aggTrade", "data": {"s": "BTCUSDT"}}-BTCUSDT]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_frame_names_its_symbol_in_the_configured_spelling[bybit-{"topic": "publicTrade.ETHUSDT", "type": "snapshot", "data": []}-ETHUSDT]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_frame_names_its_symbol_in_the_configured_spelling[okx-{"arg": {"channel": "trades", "instId": "BTC-USDT-SWAP"}, "data": [{"px": "1"}]}-BTC-USDT-SWAP]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_key_that_matches_no_layout_is_not_one[binance/raw/cex/bybit/2026/09/20/1200.jsonl.gz]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_key_that_matches_no_layout_is_not_one[raw/cex/binance/2026/09/20/12.jsonl.gz]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_key_that_matches_no_layout_is_not_one[raw/cex/binance/notes.txt]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_key_that_matches_no_layout_is_not_one[warehouse/bars/data/x.parquet]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_key_under_the_prefix_that_is_no_layout_is_refused`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_pong_an_acknowledgement_or_an_error_names_no_symbol[binance-not json at all]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_pong_an_acknowledgement_or_an_error_names_no_symbol[binance-{"result": null, "id": 1}]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_pong_an_acknowledgement_or_an_error_names_no_symbol[bybit-{"success": true, "ret_msg": "", "conn_id": "x", "op": "subscribe"}]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_pong_an_acknowledgement_or_an_error_names_no_symbol[bybit-{"success": true, "ret_msg": "pong", "op": "ping"}]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_pong_an_acknowledgement_or_an_error_names_no_symbol[okx-pong]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_pong_an_acknowledgement_or_an_error_names_no_symbol[okx-{"event": "error", "msg": "Subscribe failed", "code": "60018"}]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_second_run_over_a_finished_migration_has_nothing_to_do`
    - `tests/unit/pipeline/test_archive_rekey.py::test_a_stretch_with_no_object_is_empty_and_not_counted_as_overwritten`
    - `tests/unit/pipeline/test_archive_rekey.py::test_an_interrupted_delete_loses_nothing_and_a_second_run_finishes`
    - `tests/unit/pipeline/test_archive_rekey.py::test_an_object_naming_two_symbols_is_refused_and_left_where_it_is`
    - `tests/unit/pipeline/test_archive_rekey.py::test_an_object_of_only_acknowledgements_is_refused_not_guessed_at`
    - `tests/unit/pipeline/test_archive_rekey.py::test_layout_a_moves_to_the_symbol_directory_and_the_source_goes`
    - `tests/unit/pipeline/test_archive_rekey.py::test_layout_b_moves_and_the_venue_appears_once`
    - `tests/unit/pipeline/test_archive_rekey.py::test_the_command_is_a_dry_run_unless_told_otherwise`
    - `tests/unit/pipeline/test_archive_rekey.py::test_the_report_states_the_overwrite_as_a_number_per_symbol`
    - `tests/unit/pipeline/test_archive_rekey.py::test_the_three_layouts_are_recognised[bybit/raw/cex/bybit/2026/10/02/1059.jsonl.gz-bybit-B]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_the_three_layouts_are_recognised[raw/cex/binance/2026/09/20/1200.jsonl.gz-binance-A]`
    - `tests/unit/pipeline/test_archive_rekey.py::test_the_three_layouts_are_recognised[raw/cex/okx/BTC-USDT-SWAP/2026/09/20/0001.jsonl.gz-okx-C]`
    - `tests/unit/pipeline/test_archive_symbol.py::test_a_flush_that_writes_logs_once_even_through_s3`
    - `tests/unit/pipeline/test_archive_symbol.py::test_a_flush_with_nothing_to_write_says_nothing`
    - `tests/unit/pipeline/test_archive_symbol.py::test_an_empty_name_or_one_containing_a_slash_is_refused[-BTCUSDT]`
    - `tests/unit/pipeline/test_archive_symbol.py::test_an_empty_name_or_one_containing_a_slash_is_refused[bin/ance-BTCUSDT]`
    - `tests/unit/pipeline/test_archive_symbol.py::test_an_empty_name_or_one_containing_a_slash_is_refused[binance-BTC/USDT]`
    - `tests/unit/pipeline/test_archive_symbol.py::test_an_empty_name_or_one_containing_a_slash_is_refused[binance-]`
    - `tests/unit/pipeline/test_archive_symbol.py::test_the_key_names_venue_symbol_and_receipt_minute`
    - `tests/unit/pipeline/test_archive_symbol.py::test_two_symbols_of_one_venue_in_one_minute_leave_two_objects`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_a_lower_case_symbol_is_refused_where_the_spelling_would_split_an_instrument[binance]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_a_lower_case_symbol_is_refused_where_the_spelling_would_split_an_instrument[bybit]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_a_silence_limit_the_policy_cannot_hold_is_refused_naming_the_variable`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_binance_subscribes_through_its_url_and_sends_nothing`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_bybit_opens_its_linear_endpoint_and_subscribes_to_the_public_trade_topic`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_okx_instruments_are_accepted_as_written`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_okx_opens_the_public_endpoint_and_subscribes_with_the_instrument_as_okx_names_it`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_key_the_wiring_builds_names_the_venue_once_under_raw_cex[binance-BTCUSDT]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_key_the_wiring_builds_names_the_venue_once_under_raw_cex[bybit-BTCUSDT]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_key_the_wiring_builds_names_the_venue_once_under_raw_cex[okx-BTC-USDT-SWAP]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_session_runs_the_registrys_policy_for_the_venue[binance-BTCUSDT]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_session_runs_the_registrys_policy_for_the_venue[bybit-BTCUSDT]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_session_runs_the_registrys_policy_for_the_venue[okx-BTC-USDT-SWAP]`
    - `tests/unit/pipeline/test_build_daemon_seams.py::test_the_silence_limit_is_configuration_and_reaches_the_session`
    - `tests/unit/pipeline/test_fake_s3.py::test_a_copy_has_the_sources_size_and_etag`
    - `tests/unit/pipeline/test_fake_s3.py::test_a_corrupted_copy_does_not_match_the_source`
    - `tests/unit/pipeline/test_fake_s3.py::test_a_delete_can_be_made_to_fail_and_leaves_the_object`
    - `tests/unit/pipeline/test_fake_s3.py::test_listing_pages_and_a_missing_key_raises`
    - `tests/unit/pipeline/test_ingest_logging.py::test_an_unknown_level_is_refused_naming_the_variable[10]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_an_unknown_level_is_refused_naming_the_variable[LOUD]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_an_unknown_level_is_refused_naming_the_variable[trace]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_configure_logging_honours_the_level_in_the_environment`
    - `tests/unit/pipeline/test_ingest_logging.py::test_importing_the_daemons_module_does_not_reconfigure_the_root_logger`
    - `tests/unit/pipeline/test_ingest_logging.py::test_main_configures_logging_before_it_reads_anything_else`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_archive_says_one_line_per_object_it_writes_and_none_for_a_step`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_level_defaults_to_info_and_is_not_case_sensitive[-20]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_level_defaults_to_info_and_is_not_case_sensitive[None-20]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_level_defaults_to_info_and_is_not_case_sensitive[WARNING-30]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_level_defaults_to_info_and_is_not_case_sensitive[debug-10]`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_trade_frame_and_step_path_writes_nothing_at_info`
    - `tests/unit/pipeline/test_ingest_logging.py::test_the_trade_lines_still_exist_at_debug_for_the_day_someone_needs_them`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_connect_that_returns_and_a_reader_that_dies_again_keeps_its_backoff`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_failing_ping_is_tried_once_an_interval_and_not_on_every_tick`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_healthy_connection_is_left_alone`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_persisting_silence_does_not_log_on_every_tick`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_ping_that_cannot_be_sent_does_not_end_the_loop`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_quiet_feed_is_reconnected_even_where_the_venue_announces_its_closes[binance]`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_quiet_feed_is_reconnected_even_where_the_venue_announces_its_closes[okx]`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_reader_that_ended_without_a_close_frame_is_reconnected`
    - `tests/unit/pipeline/test_session_reconnect.py::test_a_reconnect_in_the_middle_of_a_minute_loses_nothing_the_daemon_holds`
    - `tests/unit/pipeline/test_session_reconnect.py::test_attempts_back_off_and_a_refused_connect_does_not_escape_tick`
    - `tests/unit/pipeline/test_session_reconnect.py::test_one_outage_is_one_warning_on_entry_and_one_info_on_recovery`
    - `tests/unit/pipeline/test_session_reconnect.py::test_the_silence_limit_is_not_the_venues_idle_timeout`
    - `tests/unit/pipeline/test_session_reconnect.py::test_the_stream_lifetime_reconnects_a_healthy_binance_connection`
    - `tests/unit/pipeline/test_session_reconnect.py::test_two_hundred_refusals_are_a_handful_of_log_lines_and_one_recovery`
    - `tests/unit/pipeline/test_silence_detector.py::test_a_frame_arriving_resets_the_silence_timer`
    - `tests/unit/pipeline/test_silence_detector.py::test_a_silent_connection_is_reported_with_the_venue_and_reconnected`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_blank_retired_multiplier_is_fine`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_blank_silence_limit_is_unset_not_an_error`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_is_seconds_converted_to_nanoseconds[1.5-1500000000]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_is_seconds_converted_to_nanoseconds[90-90000000000]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_that_cannot_be_meant_is_refused_naming_the_variable[-1]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_that_cannot_be_meant_is_refused_naming_the_variable[0]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_that_cannot_be_meant_is_refused_naming_the_variable[abc]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_that_cannot_be_meant_is_refused_naming_the_variable[inf]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_a_silence_limit_that_cannot_be_meant_is_refused_naming_the_variable[nan]`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_an_unset_silence_limit_leaves_the_policys_own`
    - `tests/unit/test_settings_ingest.py::TestIngestSettingsEnv::test_the_retired_multiplier_is_refused_and_not_quietly_ignored`
- **Code:**
    - `src/channelflow/bars/builder.py`
    - `src/channelflow/connectors/binance/connector.py`
    - `src/channelflow/connectors/bybit/connector.py`
    - `src/channelflow/connectors/okx/connector.py`
    - `src/channelflow/connectors/session.py`
    - `src/channelflow/connectors/subscribing.py`
    - `src/channelflow/connectors/venue.py`
    - `src/channelflow/connectors/websocket.py`
    - `src/channelflow/pipeline/archive.py`
    - `src/channelflow/pipeline/archive_rekey.py`
    - `src/channelflow/pipeline/ingest.py`
    - `src/channelflow/pipeline/ingest_main.py`
    - `tools/record/parity_capture.py`
- **Outcomes:** [[OUT-2026-10-02-implement-ingest-resilience]], [[OUT-2026-10-02-plan-ingest-resilience]], [[OUT-2026-10-02-spec-ingest-resilience]], [[OUT-2026-10-02-tasks-ingest-resilience]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
