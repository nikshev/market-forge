---
id: OUT-2026-09-08-implement-telegram-alerting
step: implement
records: [REQ-WP-008]
commit: null
---

## What was done

`channelflow.alerting`: the alert and its derived id, PRD §26.1's message and
§27.1's deep link, §26.2's dedupe, §26.4's retry and dead-lettering, and
§25.6's staleness gate. 33 tests, no network, no clock.

This is the first half of [[ADR-010]]'s gap: `ALERTED` now has something that
performs it.

## What was decided

- **`_moment` divides before constructing the datetime.** Going through a float
  loses nanosecond precision, and a timestamp drifting by a microsecond between
  two renders would break FR-005's determinism for a reason nobody would find.
- **Only the literal `"ok"` counts as delivered.** An ambiguous response is
  retried: a delivery nobody can confirm is not a delivery, and
  `test_an_unexpected_response_is_treated_as_a_failure` pins it.
- **The dedupe key is the market, the value is the setup.** Keyed by
  `(venue, symbol, timeframe)` because the cooldown is about how often a reader
  hears from one market; the stored signal id and state are what decide whether
  this particular thing has been said. Keyed by signal id alone, every new
  candidate would bypass the cooldown.
- **Attempt timestamps are derived from the queue time plus the computed
  backoff**, not read from anywhere. That is what makes the audit identical on
  a replay (ADR-018, Principle VII).

## A test bug worth recording

`test_a_section_with_no_data_is_absent_by_heading` asserted `"Channel" not in
message` — which failed, because "Channel" also occurs inside the setup name
"Upper Channel Rejection". The substring check was wrong in both directions: it
would also have *passed* for a renderer emitting `Channel:` with no body. It
now checks whole lines. A heading test that matches substrings is not testing
headings.

## Mutation results

Six mutations, all caught, with `__pycache__` cleared between steps:

| Mutation | Caught by |
| --- | --- |
| Let a repeat of the same state through | `test_the_same_state_offered_again_is_refused` |
| Let the cooldown alone re-arm, with no new touch | `test_an_elapsed_cooldown_alone_does_not_allow_a_new_alert` |
| Deliver from a stale book | `test_a_stale_book_suppresses_the_alert` |
| Swallow the dead letter | `test_a_transport_that_always_fails_dead_letters` |
| Let a transport exception escape | `test_a_throwing_transport_never_reaches_the_caller` |
| Generate a random signal id | `test_the_signal_id_is_the_same_for_the_same_candidate` (+6) |

The random-id mutation was the one predicted to be dangerous, and it behaved as
predicted: `uuid4()` is what a UUID field usually holds, nothing crashes, and
seven tests across three files fail only because the id was pinned as derived.
Without those, a replay would have produced a different audit from identical
input and nothing would have said so.

## What is still open

- **No Telegram transport ships here.** The protocol is defined and the adapter
  is owed — small, and behind the connector boundary ([[ADR-018]]).
- **The deep link points at a chart that does not exist** ([[REQ-WP-009]]).
- **Nothing is durable.** The audit and dead-letter list are in memory; PRD
  §29's storage is unbuilt, so a restart loses both.
- **No severity and no score** ([[ADR-016]]). PRD §26.3's tiers arrive with
  §43's ranker.
- **The caller owns the retry loop.** This package decides *how long* to wait
  and never waits.
