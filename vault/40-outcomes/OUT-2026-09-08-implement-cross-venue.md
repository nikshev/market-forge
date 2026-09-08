---
id: OUT-2026-09-08-implement-cross-venue
step: implement
records: [REQ-WP-016]
commit: null
---

## What was done

`channelflow.crossvenue`: PRD §17's consensus price, cross-venue basis,
fragmentation and lead-lag. 36 tests.

## The two prohibitions

§17 states two things nobody can compute, and both had to become facts the suite
can check.

**§18.14 — no mid-based basis for an AMM.** §17.3's formula is arithmetically
well-defined for a pool and economically meaningless there, which is the exact
shape of mistake that yields a plausible number. `basis_bps` refuses for any
venue that is not an order book; `executable_basis_bps` at a caller-supplied
notional is the answer instead. There is no default notional, because at zero
size every venue costs the same.

**§17.2 — no trading rule from a correlation.** Intent is not checkable, so the
prohibition became structure ([[ADR-040]]): `leadlag` is not re-exported, every
output carries `research_only`, and a test walks the signal, alerting and stop
packages asserting none of them imports it. That test also asserts those three
packages still exist — otherwise deleting one would turn the check green.

## Three tests that were wrong, and one thing they showed

Three lead-lag tests used windows reaching back before their fixture's first
price, and expected a number. The code returned nothing, which is correct: a
10-second return computed over the 5 seconds available is a 5-second return
wearing the wrong label. The tests were fixed, not the code — including one
expectation corrected from `0.0` to `log(3030/3000)`, which is the other half of
the same mistake: zero is what "no movement" looks like, and "no answer" needs
to look different from it.

## What was decided

- **Executable prices are supplied, not computed** ([[ADR-039]]). Fees, gas and
  MEV margins belong to the caller who knows their venue.
- **Comparability comes from the registry** ([[REQ-ASSET-001]]), never from
  tickers.
- **An even contributor count is reported.** The median of an even set is
  interpolated rather than observed, and a reader deciding how much to trust the
  figure needs to know which one they have.
- **Ties in the best-execution ranking break on venue id**, so two runs over one
  input agree.

## Mutation results

Eight mutations, all caught, every restore verified and the tree swept
afterwards:

| Mutation | Caught by |
| --- | --- |
| The staleness check is removed | `test_a_stale_venue_does_not_contribute` (+1) |
| The future-quote check is removed | `test_a_quote_from_after_the_instant_does_not_contribute` |
| One contributor is enough for a consensus | `test_fewer_than_two_contributors_is_refused` |
| The cross-asset check is removed | `test_venues_quoting_different_assets_are_refused` |
| Mid-based basis is allowed for an AMM | `test_mid_basis_is_refused_for_an_amm` |
| The best venue is chosen by headline price | `test_the_best_venue_is_chosen_by_all_in_cost_not_headline_price` |
| Unfillable venues are ranked instead of excluded | `test_a_venue_that_cannot_fill_is_excluded_and_reported` (+1) |
| The return window's floor is ignored | `test_a_window_with_nothing_to_open_against_is_absent_not_zero` |

The second is the look-ahead one: without it a quote observed after the instant
contributes to a consensus about that instant, and every downstream figure
inherits the leak while looking ordinary.

## What is still open

- **Nothing consumes the engine yet.** §44A.15 wants the fragmentation input;
  wiring it is separate work.
- **No lead-lag trading rule**, and none until out-of-sample validation exists —
  which is the point of the import ban, not a limitation of it.
