---
id: REQ-WP-021
title: An instrument's trading rules are ingested, stored and served
type: work-package
prd_ref: "Phase 1 — CEX channel MVP; §29.B; §41 rule 9"
prd_lines: "6702-6702"
phase: 1
status: implemented
depends_on: [REQ-WP-003, REQ-STORE-002, REQ-API-001]
tags: []
---

## Requirement

PRD §45's Phase 1 deliverables list, one line:

    - basic market metadata;

That is all the PRD says. No section elaborates it, none of Phase 1's five
acceptance criteria depends on it, and it is the last of Phase 1's twelve
deliverables with nothing behind it — which is why [[REQ-PHASE-1]] cannot leave
`planned`.

So "basic" is derived rather than quoted, from what the rest of this system
would need to know before it could claim a trade was realisable:

- **the price increment** (`tick_size`). A backtest that fills at a price the
  venue cannot quote has filled at a price that does not exist.
- **the quantity increment** (`step_size`) and **the minimum notional**. A
  position below the venue's minimum, or off its size grid, is not a trade
  anybody could place, and counting it inflates a result. PRD §41 rule 9 governs
  any economic evaluation.
- **the assets** (`base_asset`, `quote_asset`) and **the contract size**, without
  which a perp's quantity is a number with no unit.
- **the trading status**, because an instrument that is halted is not one a
  signal can be opened on, and its absence and its halt are different facts.

Today the system knows a market by `venue`, `symbol` and `market_type` and
nothing else.

## Acceptance

- an exchange's instrument payload is normalized into instrument values, with
  the venue's own field names left at the boundary;
- a payload missing a field this requirement names is refused rather than
  defaulted — a tick size guessed at is worse than one absent;
- decimal quantities stay decimal end to end, with no float in the path;
- instruments are stored on the canonical plane and read back identically;
- an instrument recorded twice does not appear twice;
- the API serves an instrument's rules with the market it belongs to, and the
  in-memory and lakehouse repositories answer alike;
- no endpoint's existing fields change.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-060-instrument-metadata]]
- **Tests:**
    - `tests/unit/api/test_repository_conformance.py::test_a_market_carries_the_rules_it_was_stored_with[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_carries_the_rules_it_was_stored_with[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_described_twice_appears_once[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_described_twice_appears_once[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_stored_without_rules_has_them_absent[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_market_stored_without_rules_has_them_absent[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_a_spot_market_has_no_contract_size[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_a_spot_market_has_no_contract_size[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_every_decimal_survives_the_round_trip_exactly[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_every_decimal_survives_the_round_trip_exactly[lakehouse]`
    - `tests/unit/api/test_repository_conformance.py::test_one_venue_s_rules_are_not_returned_for_another[in_memory]`
    - `tests/unit/api/test_repository_conformance.py::test_one_venue_s_rules_are_not_returned_for_another[lakehouse]`
    - `tests/unit/connectors/binance/test_instruments.py::test_a_float_in_the_payload_is_refused_rather_than_converted`
    - `tests/unit/connectors/binance/test_instruments.py::test_a_missing_filter_is_refused_naming_the_symbol_and_the_field`
    - `tests/unit/connectors/binance/test_instruments.py::test_a_payload_with_no_symbols_is_refused`
    - `tests/unit/connectors/binance/test_instruments.py::test_a_repeated_symbol_keeps_the_later_entry`
    - `tests/unit/connectors/binance/test_instruments.py::test_a_spot_entry_has_no_contract_size`
    - `tests/unit/connectors/binance/test_instruments.py::test_every_entry_becomes_one_instrument`
    - `tests/unit/connectors/binance/test_instruments.py::test_numbers_arrive_as_strings_and_stay_decimal`
    - `tests/unit/connectors/binance/test_instruments.py::test_the_venue_s_field_names_stop_at_the_boundary`
    - `tests/unit/domain/test_instrument.py::test_a_contract_size_of_zero_is_refused`
    - `tests/unit/domain/test_instrument.py::test_a_float_rule_is_refused`
    - `tests/unit/domain/test_instrument.py::test_a_negative_rule_is_refused[min_notional]`
    - `tests/unit/domain/test_instrument.py::test_a_negative_rule_is_refused[step_size]`
    - `tests/unit/domain/test_instrument.py::test_a_negative_rule_is_refused[tick_size]`
    - `tests/unit/domain/test_instrument.py::test_a_rule_of_zero_is_refused[min_notional]`
    - `tests/unit/domain/test_instrument.py::test_a_rule_of_zero_is_refused[step_size]`
    - `tests/unit/domain/test_instrument.py::test_a_rule_of_zero_is_refused[tick_size]`
    - `tests/unit/domain/test_instrument.py::test_a_spot_instrument_has_no_contract_size`
    - `tests/unit/domain/test_instrument.py::test_an_empty_name_is_refused`
    - `tests/unit/domain/test_instrument.py::test_an_instrument_carries_every_rule_it_was_given`
- **Code:**
    - `src/channelflow/connectors/binance/instruments.py`
    - `src/channelflow/domain/instrument.py`
- **Outcomes:** [[OUT-2026-09-10-implement-instrument-metadata]], [[OUT-2026-09-10-plan-instrument-metadata]], [[OUT-2026-09-10-requirement-instrument-metadata]], [[OUT-2026-09-10-spec-instrument-metadata]]
<!-- trace:end -->

## Notes

Extracted by hand. The PRD line is a deliverable with no section behind it, and
`tools/extract_prd.py` would have written `ACCEPTANCE-NOT-SPECIFIED`. The
acceptance above is **derived**, and the derivation is the body of this note: each
field is there because something downstream cannot be correct without it, not
because exchanges publish it.

**Using the rules is deliberately not in scope.** Rounding a fill to a valid
tick, refusing a size below the minimum, and skipping a halted instrument are
each a change to the backtest's execution model, and each deserves its own
requirement rather than arriving as a side effect of an ingestion deliverable.
What is in scope is that the numbers exist, are right, and are reachable — so
this does not repeat the pattern [[REQ-STORE-001]], [[REQ-TBL-001]] and
[[REQ-BIAS-011]] each recorded in turn, where a mechanism was built and nothing
used it: the API serves these the moment they are stored.

Fetching the payload over HTTP is out of scope for the same reason the rest of
[[REQ-WP-003]] keeps the wire behind a `Transport` protocol — the normalizer
takes a payload, and where the payload came from is the caller's business.
