---
id: REQ-WP-066
title: The ingest daemon feeds the stack from a live venue
type: work-package
prd_ref: "§6.2, §6.4.4, §7, §45 Phase 8"
prd_lines: "405-420, 598-615, 735-745, 6904-6913"
phase: 8
status: implemented
depends_on: [REQ-WP-064, REQ-WP-065, REQ-WP-051, REQ-PIPE-001]
tags: []
---

## Requirement

PRD §6.2 names `ingest-binance` among the MVP deployment's services.
[[REQ-PIPE-001]] deferred it in writing — "a live process attaching the same
sinks to a running connector is deployment work and adds nothing this cannot
already show" — and that was right about what a replay demonstrates and silent
about what a deployment needs. **A stack nobody can feed shows nothing**, and
everything from [[REQ-WP-064]]'s images to §27's chart is waiting on it.

### The parts that decide already exist

[[REQ-WP-051]]'s `StreamSession` owns the connection's life and is tested against
a `FakeClock`; `normalize` turns a frame into a `TradeEvent`; `BarBuilder` closes
bars; `BarSink` commits them. What is missing is the loop, and it must be
arranged so **the untestable part — a real socket — is the part with no
decisions in it.**

`Transport` is already a protocol, so the live socket and a replay over recorded
frames are two implementations of one seam, the way `lakehouse.catalog` is one
implementation behind two URLs ([[ADR-002]]). CI runs the daemon, not a
rehearsal of it.

### The loop's shape is dictated by the venue

Measured on 2026-09-13 against `stream.binance.com`: a protocol PING every **20
seconds** — intervals 20.0, 20.1, 19.9, 20.1 over 400 seconds — and the venue
drops a client that does not answer. `websockets` answers automatically, but
from the connection's own task, which runs only while its event loop does.

So normalising a frame, compressing an archive object or committing to Iceberg
on that loop would stop the pongs, and the venue would drop the connection **with
no error and no close frame**. The socket therefore does nothing but I/O, and
everything expensive happens on the other side of a queue.

### The raw tier is objects, not a table

§6.4.4 lays out `s3://channel-flow/raw/cex/...`, and line 642: raw immutable
payloads "may remain plain compressed objects/Parquet when Iceberg metadata adds
no value". It adds none — a frame has no schema to evolve, is never updated, and
arrives ten times a second.

§7 calls this the tier "where re-normalization may be required": a parsing
mistake found next month can be repaired over the originals, and without them
those days are gone. Measured for one symbol on two streams: 800 frames a
minute, **556 MiB a day raw**, 12.3% of that compressed. The compression is what
makes the tier affordable.

## Acceptance

- A daemon connects to the venue, and the API serves bars built from it.
- Every frame is archived **before** anything is decided about it, including one
  this build cannot read.
- One compressed object per minute; a quiet minute writes none; a frame comes
  back byte-identical.
- A frame that cannot be parsed or normalised is counted and does not stop the
  ingest; a stream this build does not consume is counted, not dropped silently.
- Shutdown commits before it closes.
- Stream names are lower-cased — measured: the upper-case form connects and
  delivers nothing.
- The same daemon runs over recorded frames, which is what CI exercises.
- Configuration refuses a missing symbol list or archive location.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-107-ingest-daemon]]
- **Tests:**
    - `tests/unit/pipeline/test_ingest.py::test_a_backwards_clock_is_refused`
    - `tests/unit/pipeline/test_ingest.py::test_a_bad_frame_does_not_stop_the_ingest`
    - `tests/unit/pipeline/test_ingest.py::test_a_frame_survives_the_round_trip_byte_for_byte`
    - `tests/unit/pipeline/test_ingest.py::test_a_frame_that_cannot_be_normalized_is_counted`
    - `tests/unit/pipeline/test_ingest.py::test_a_quiet_minute_writes_no_object`
    - `tests/unit/pipeline/test_ingest.py::test_a_send_before_connect_is_refused`
    - `tests/unit/pipeline/test_ingest.py::test_a_step_reports_what_it_did`
    - `tests/unit/pipeline/test_ingest.py::test_a_stream_this_build_does_not_consume_is_counted_not_dropped`
    - `tests/unit/pipeline/test_ingest.py::test_a_timeframe_that_spans_nothing_is_refused`
    - `tests/unit/pipeline/test_ingest.py::test_a_written_object_is_not_written_again`
    - `tests/unit/pipeline/test_ingest.py::test_every_frame_is_archived_before_anything_is_decided`
    - `tests/unit/pipeline/test_ingest.py::test_every_frame_refreshes_the_session`
    - `tests/unit/pipeline/test_ingest.py::test_one_object_per_minute`
    - `tests/unit/pipeline/test_ingest.py::test_recorded_frames_become_trades`
    - `tests/unit/pipeline/test_ingest.py::test_stopping_commits_before_it_closes`
    - `tests/unit/pipeline/test_ingest.py::test_the_archive_compresses`
    - `tests/unit/pipeline/test_ingest.py::test_the_archive_scheme_chooses_the_store`
    - `tests/unit/pipeline/test_ingest.py::test_the_fixture_is_what_the_venue_sent`
    - `tests/unit/pipeline/test_ingest.py::test_the_flush_interval_is_a_minute_not_a_bar`
    - `tests/unit/pipeline/test_ingest.py::test_the_key_is_dated_and_nested_by_day`
    - `tests/unit/pipeline/test_ingest.py::test_the_live_transport_delivers_frames_across_the_thread`
    - `tests/unit/pipeline/test_ingest.py::test_the_order_of_shutdown_is_commit_then_close`
    - `tests/unit/pipeline/test_ingest.py::test_the_pong_is_deliberately_silent`
    - `tests/unit/pipeline/test_ingest.py::test_the_queue_depth_is_visible`
    - `tests/unit/pipeline/test_ingest.py::test_the_replay_transport_is_the_same_seam`
    - `tests/unit/pipeline/test_ingest.py::test_the_stream_names_are_lower_case`
    - `tests/unit/pipeline/test_ingest.py::test_the_symbols_and_the_archive_are_required`
    - `tests/unit/pipeline/test_ingest.py::test_the_timeframe_defaults_to_a_minute`
    - `tests/unit/pipeline/test_ingest.py::test_trades_become_a_bar_the_builder_closes`
- **Code:**
    - `src/channelflow/connectors/websocket.py`
    - `src/channelflow/pipeline/archive.py`
    - `src/channelflow/pipeline/ingest.py`
    - `src/channelflow/pipeline/ingest_main.py`
    - `src/channelflow/settings.py`
- **Outcomes:** [[OUT-2026-09-13-implement-ingest-daemon]]
<!-- trace:end -->

## Notes

Only `@aggTrade` becomes events: bars need trades, and a book this build does not
maintain would be a half-built one. Depth is archived and counted as ignored, so
the gap is visible rather than inferred.

A live daemon produces one candle per timeframe, so a chart is empty until the
first bar closes. Seeding history is separate, and not a shortcut: `Bar` refuses
a venue kline because it requires `low_time_ns`, `high_time_ns`,
`first_trade_id` and `last_trade_id`, which a kline does not carry.

`worker` remains unbuilt. §6.2 names it, nothing in this repository is one, and
writing a service to have something to containerise would repeat the mistake
[[REQ-PIPE-001]] avoided.
