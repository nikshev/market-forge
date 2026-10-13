---
id: REQ-WP-107
title: "The venue basis is looked up by bisection: the features series no longer spends three seconds comparing every bar with every quote"
type: work-package
prd_ref: "§36, §17.3; measured 2026-10-13"
prd_lines: "6034-6052"
phase: null
status: implemented
depends_on: [REQ-WP-091, REQ-WP-104]
tags: [performance, api, consensus]
hard_gated: false
---

## Requirement

After [[REQ-WP-104]] the features series was still the slowest read: 2-4.5 s. Profiled inside the API, the repository answered in **0.75 s**
and the HTTP request took 3.8 s: the route merges the venue basis into the series, and `select_venue_basis` scanned **every quote the table
held for every bar** of the answer -- a day of one-minute bars against days of quotes of every venue, tens of millions of comparisons, on
rows that had each been made a Python dict first.

1. The viewed venue's quotes are **narrowed in Arrow** (venue, symbol, none after the window's end) before any row becomes a dict.
2. They are ordered once by exchange time and **bisected** per bar. The answer is unchanged: the newest quote at or before the close, a
   quote exactly at the close available at it, and of two quotes with one exchange time the one stored first.

## Acceptance

- The newest quote at or before the close is used; one at the close counts; a tie keeps the first stored; another venue's or symbol's
  quote is not this one's; a bar with no quote before it is skipped, not zero; the quotes may arrive in any order (tests).
- A day of one-minute bars against three days of quotes of two venues takes under a second (test; it took seconds).
- On the running stack the features series answers in about a second.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-159-venue-basis-cost]]
- **Tests:**
    - `tests/unit/api/test_venue_basis_cost.py::test_a_bar_with_no_quote_at_or_before_it_is_skipped_not_zero`
    - `tests/unit/api/test_venue_basis_cost.py::test_a_day_of_bars_against_days_of_quotes_is_not_a_second_of_work`
    - `tests/unit/api/test_venue_basis_cost.py::test_a_quote_exactly_at_the_close_is_available_at_it`
    - `tests/unit/api/test_venue_basis_cost.py::test_a_refused_consensus_and_other_assets_are_skipped_as_before`
    - `tests/unit/api/test_venue_basis_cost.py::test_another_venue_or_symbol_is_not_this_ones_quote`
    - `tests/unit/api/test_venue_basis_cost.py::test_of_two_quotes_with_the_same_exchange_time_the_first_stored_wins`
    - `tests/unit/api/test_venue_basis_cost.py::test_shuffled_quotes_give_the_answer_that_ordered_quotes_give`
    - `tests/unit/api/test_venue_basis_cost.py::test_the_newest_quote_at_or_before_the_close_is_the_one_used`
    - `tests/unit/api/test_venue_basis_cost.py::test_the_quotes_may_arrive_in_any_order`
- **Code:**
    - `src/channelflow/api/lakehouse_repository.py`
    - `src/channelflow/api/repositories.py`
- **Outcomes:** [[OUT-2026-10-13-implement-venue-basis-cost]]
<!-- trace:end -->
