---
id: REQ-WP-108
title: "The price moves on the last bar as it does on Investing: updates reach the page within a fraction of a second, and the chart opens where the last bar can be seen"
type: work-package
prd_ref: "§13, §36; owner's direction 2026-10-13"
prd_lines: "6034-6052"
phase: null
status: implemented
depends_on: [REQ-WP-102, REQ-WP-106]
tags: [live, chart, performance]
hard_gated: false
---

## Requirement

On 2026-10-13 the owner compared the chart with Investing's: there the price visibly moves on the last bar; here it did not, although
[[REQ-WP-102]] and [[REQ-WP-106]] delivered a live socket and a live window on every timeframe. Four causes, each measured:

1. **The consumer slept.** `consume(num_messages, timeout)` of the Kafka client returns when the count is reached *or the timeout passes*,
   so a poll asked for 500 messages waited the whole second for the 499 that were not coming. Forming bars arrived in one-second bursts. A
   poll now waits at most 50 ms per call.
2. **Replay went to the browser.** The one topic held finals and forming bars, kept seven days (the default of a topic created before
   retention was enforced) and was replayed on every start: about 230,000 messages, 38 s of catch-up, all forwarded. Finals
   (`market.bar_final.v1`, 30 min, replayed to fill the cache, **not forwarded**) and forming bars (`market.bar_forming.v1`, 5 min, only
   the latest) are two topics, and an existing topic is brought to the asked retention.
3. **The publisher repeated itself.** A forming bar is published four times a second per series, and only when its shape (open time, OHLC,
   volume) has changed.
4. **The chart opened on the wrong view.** The visible range ended at the last *stored* bar and spanned the whole history: the live bars
   were off the right edge, or a few pixels wide under the volume profile. It now opens on the newest 150 bars with room on the right
   (30 % with the profile overlay, 5 % without) and follows the newest bar while the reader is at it.

## Acceptance

- A poll that has received a message returns without waiting out its timeout (test).
- A final goes to the final topic, a forming bar to the forming topic; a final is replayed to rebuild the cache and is not forwarded; a
  forming bar is forwarded at once (tests; integration test through a real broker, including a topic that already existed with another
  retention).
- An unchanged forming bar is not published twice; a changed one is, at most four times a second (tests; mutation sweep).
- The chart opens on the newest bars with the newest bar clear of the volume profile, and follows new bars only while the reader is at the
  newest one (vitest).
- On the running stack the socket delivers several price changes a second and the price label on the chart moves, on 1m and on 4h.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-160-price-moves-live]]
- **Tests:**
    - `tests/unit/transport/test_kafka_poll_latency.py::test_a_message_that_arrives_is_returned_without_waiting_for_the_deadline`
    - `tests/unit/transport/test_kafka_poll_latency.py::test_an_empty_topic_still_waits_out_the_timeout_and_answers_empty`
    - `tests/unit/transport/test_kafka_poll_latency.py::test_no_single_wait_is_longer_than_a_tenth_of_a_second`
    - `tests/unit/web/test_live_view_artifacts.py::test_every_module_this_requirement_touches_names_it[Chart.tsx]`
    - `tests/unit/web/test_live_view_artifacts.py::test_every_module_this_requirement_touches_names_it[series.ts]`
    - `tests/unit/web/test_live_view_artifacts.py::test_the_behaviour_is_covered_by_a_vitest_file_that_names_the_requirement`
    - `tests/unit/web/test_live_view_artifacts.py::test_the_chart_opens_on_the_newest_bars_not_on_the_whole_history`
    - `tests/unit/web/test_live_view_artifacts.py::test_the_number_of_bars_shown_is_small_enough_for_the_last_bar_to_be_seen`
- **Code:**
    - `apps/web/src/Chart.tsx`
    - `apps/web/src/series.ts`
    - `src/channelflow/live/broker.py`
    - `src/channelflow/live/messages.py`
    - `src/channelflow/live/publisher.py`
    - `src/channelflow/live/relay.py`
    - `src/channelflow/transport/kafka.py`
- **Outcomes:** [[OUT-2026-10-13-implement-price-moves-live]]
<!-- trace:end -->
