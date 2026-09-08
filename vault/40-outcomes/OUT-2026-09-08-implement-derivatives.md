---
id: OUT-2026-09-08-implement-derivatives
step: implement
records: [REQ-WP-013, REQ-BIAS-005]
commit: null
---

## What was done

`channelflow.derivatives`: PRD §16's funding, open interest, basis and
liquidation features, with the settlement boundary that makes funding legal.
38 tests, 16 registered features.

REQ-BIAS-005 moves to `implemented`. [[ADR-016]]'s missing derivatives block in
the alert message now has a source.

## What was decided

- **`exposed_feature_names()` now reads both feature packages.** The registry
  test compares exposed against registered, and the enumeration previously read
  only REQ-WP-011's package — so this package could have shipped sixteen
  unregistered features with the gate still green. [[ADR-015]]'s gate is about
  the system only if the enumeration is.
- **`settled_funding` is the only place `funding_rate` is read.** Nothing else
  in the module touches it, so the boundary cannot be bypassed by a later
  feature written in a hurry.
- **A later ingest time wins at the same event time.** Two states for one
  instant is a venue correcting itself; equal on both is a tie nothing in the
  data breaks, and it refuses.
- **Liquidation clusters bucket relative to a reference price**, not in
  absolute currency. An absolute bucket size tuned on one symbol is meaningless
  on another.
- **`UNDETERMINED` is not in PRD §16.2 and is necessary.** A flat leg is in
  none of the four quadrants, and forcing it into one would invent a reading.

## Two of my own arithmetic errors, both in tests

- **The mark-premium test divided by the wrong leg.** It expected -20 bps from
  a ratio that gives -19.96 — precisely the error using the mark instead of the
  index produces, and small enough to have been waved through as floating-point
  noise. The test now uses numbers where the correct denominator gives exactly
  -20, and says so.
- **The liquidation window test misread its own boundary.** `(as_of - window,
  as_of]` at minute 15 with a two-minute window is minutes 14 and 15, which
  contain nothing; I had written it expecting minutes 11 and 12. Moved to
  minute 12, where the 100,000 print at minute 10 sits exactly on the excluded
  edge — which is what the test should have been pinning all along.

## Mutation results

Five mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An unsettled funding rate is used | `test_an_unsettled_rate_is_not_used_at_t` (+3) |
| The z-score returns zero on a constant series | `test_a_constant_series_has_no_z_score` |
| The join takes a later state | `test_the_join_never_returns_a_later_state` (+1) |
| A zero denominator returns zero | `test_the_ratio_is_absent_on_no_volume` (+2) |
| A feature loses its registration | `test_every_exposed_feature_is_registered` |

The last confirms the gate now covers this package rather than only the one it
was built in.

## What is still open

- **Cross-venue dispersion** (§16.1, §16.3) is REQ-WP-016; the DEX leg is
  REQ-WP-014/015.
- **§16.5's long/short ratios are not built** — optional in the PRD, and with
  one provider the required "provider-specific" label would be the only
  content.
- **Nothing wires these into the alert message yet.** [[ADR-016]] omits the
  derivatives block for want of a source; the source now exists, and connecting
  them is REQ-WP-008's territory to revisit.
