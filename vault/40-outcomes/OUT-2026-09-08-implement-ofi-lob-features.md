---
id: OUT-2026-09-08-implement-ofi-lob-features
step: implement
records: [REQ-WP-011, REQ-PRIN-008]
commit: null
---

## What was done

`channelflow.features`: registry, instant book features, OFI, trade flow, wall
lifecycle. 24 registered features, 52 tests.

## What was decided

- **The registry gate held from the first commit onward.** Phase 1 left
  `test_every_exposed_feature_is_registered` red, and it stayed red through
  every later phase until the last feature was registered. That is the
  behaviour [[ADR-015]] wanted: a feature cannot reach a green suite
  undocumented.
- **`FeatureSpec` gives no field a default.** A default is a field an author
  can skip thinking about, and `availability_lag_ms` or `null_policy` left at
  someone else's guess is the documentation this is meant to prevent.
- **The Cont indicators are non-strict on both sides, deliberately.** When a
  price is unchanged both fire and the term collapses to the change in size.
  Writing them strictly gives a function that is correct whenever the touch
  moves and silently wrong the rest of the time — which is most of the time.
  `test_an_unchanged_bid_price_contributes_the_size_change` exists for that one
  case.
- **An unknown aggressor counts as volume and as neither side.** Dropping the
  trade understates volume; guessing a side invents flow. Both errors are
  invisible in the output, so the third option is the only honest one.
- **`normalized_delta` is absent, not zero, on an empty window.** Zero means
  the buys and sells cancelled. A caller reading a silent minute as perfectly
  balanced is acting on a fact that did not happen. Same reason `OFIWindow`
  carries an observation count.

## Two mistakes worth recording

- **Two of my own test expectations were wrong, not the code.** The OFI window
  test assumed a one-second window held one increment when it held three, and
  the CVD slope test assumed a trade on the window's lower edge was inside it.
  Both were arithmetic errors in the test, and both are now written so the
  half-open convention is visible: the slope test asserts that slope equals the
  window's own delta per second, which only holds if the boundary is exclusive.
- **A mutation run reported a false result.** Restoring a mutated file with
  `cp` left a `.pyc` newer than the restored source, so a clean file kept
  running mutated bytecode and two unrelated tests appeared to fail. The whole
  sweep was re-run with `__pycache__` cleared between steps. A mutation harness
  that does not clear bytecode can report a guard as caught when it was not.

## Mutation results

Eight mutations, all caught, re-run with bytecode cleared:

| Mutation | Caught by |
| --- | --- |
| Compute an OFI increment across a gap | `test_no_increment_is_computed_across_a_gap` |
| Attribute a wall's whole decrease to execution | `test_executed_never_exceeds_what_actually_traded_there` (+3) |
| Let a registration's name drift from its feature | `test_every_exposed_feature_is_registered` |
| Take window boundaries from ingest time | `test_the_cvd_slope_is_the_change_across_the_window_per_second` (+4) |
| Return 0.0 instead of refusing a zero denominator | `test_queue_imbalance_refuses_two_zero_sized_touches` |
| Weight the microprice by the same side | `test_the_microprice_leans_away_from_the_larger_queue` |
| Stop counting refills | `test_a_wall_that_grows_again_is_a_refill_not_a_new_wall` |
| Reverse the bid-side top-N ordering | `test_depth_imbalance_over_a_symmetric_book_is_zero` |

The microprice mutation is the instructive one. The balanced-book case passes
under *both* weightings, so the test that catches it has to be the lopsided one
— a suite built only on symmetric fixtures would have missed a formula
inverted at its core.

## What is still open

- **No CVD-price divergence** ([[ADR-013]]), and a test asserts its absence so
  adding one means revisiting the ADR rather than quietly filling the gap.
- **PRD §15.5's remaining shape features and §15.7's absorption** have no
  requirement note yet — deferred extraction, like §35.3/§35.4 for rule R5.
- **REQ-WP-006's channel quality submetrics remain unregistered** ([[ADR-015]]).
- **Nothing is persisted.** PRD §24.1's feature snapshot table is unbuilt, so
  every tracker's history lives only in memory and only for the process.
- **`_cvd_at` walks the whole history per call.** Linear where a bisect would
  be logarithmic; PRD §0.14 puts correctness first, and this is a profile away
  from mattering.
