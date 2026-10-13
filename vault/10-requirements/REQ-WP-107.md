---
id: REQ-WP-107
title: "The venue basis is looked up by bisection: the features series no longer spends three seconds comparing every bar with every quote"
type: work-package
prd_ref: "§36, §17.3; measured 2026-10-13"
prd_lines: "6034-6052"
phase: null
status: tested
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
<!-- trace:end -->
