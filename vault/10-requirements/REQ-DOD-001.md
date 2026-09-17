---
id: REQ-DOD-001
title: PRD §47's nineteen conditions, each named by what delivers it
type: constraint
prd_ref: "§47"
prd_lines: "7137-7163"
phase: null
status: implemented
depends_on: []
tags: []
hard_gated: false
covers: [REQ-WP-004, REQ-WP-006, REQ-WP-007, REQ-WP-008, REQ-WP-010, REQ-WP-015, REQ-WP-017, REQ-WP-018, REQ-WP-019, REQ-WP-020, REQ-WP-023, REQ-WP-024, REQ-WP-028, REQ-WP-032, REQ-WP-033, REQ-WP-034, REQ-WP-046, REQ-WP-072, REQ-SCORE-001, REQ-REPRO-001, REQ-EXP-004, REQ-EXP-008, REQ-EXP-009, REQ-EXP-010, REQ-EXP-013, REQ-EXP-017, REQ-US-006, REQ-NRT-A, REQ-NRT-F, REQ-NRT-REPAINT]
conditions:
  - item: 1
    text: "Non-repainting channel proven by automated tests."
    covers: [REQ-WP-006, REQ-NRT-A, REQ-NRT-REPAINT]
  - item: 2
    text: "Signals stored with exact point-in-time feature snapshots."
    covers: [REQ-WP-007, REQ-WP-017]
  - item: 3
    text: "Telegram deep-link works."
    covers: [REQ-WP-008]
  - item: 4
    text: "Backtest uses same signal engine."
    covers: [REQ-WP-010]
  - item: 5
    text: "CEX L2 reconstruction has gap protection."
    covers: [REQ-WP-004]
  - item: 6
    text: "Volume/OFI/derivatives can be toggled in score."
    covers: [REQ-SCORE-001]
  - item: 7
    text: "DeFi ingestion reconstructs protocol-native state and produces validated executable-depth features across at least one CL AMM and one invariant AMM."
    covers: [REQ-WP-015, REQ-WP-046]
  - item: 8
    text: "Walk-forward report exists."
    covers: [REQ-WP-024]
  - item: 9
    text: "Channel-only vs enriched-feature ablation exists."
    covers: [REQ-US-006, REQ-EXP-004]
  - item: 10
    text: "At least one probability model is calibrated and compared against logistic baseline."
    covers: [REQ-WP-023, REQ-EXP-009]
  - item: 11
    text: "GMDH is treated as candidate, not assumed winner."
    covers: [REQ-WP-018, REQ-EXP-008]
  - item: 12
    text: "Research report explicitly states when there is no detectable edge."
    covers: [REQ-REPRO-001, REQ-EXP-010]
  - item: 13
    text: "Confirmed extrema preserve separate `extremum_time` and `known_at`."
    covers: [REQ-WP-019, REQ-WP-028]
  - item: 14
    text: "Turning-point forecasts expose explicit horizon and calibrated P(max)/P(min)/P(no-turn)."
    covers: [REQ-WP-023]
  - item: 15
    text: "GMDH derivative roots cannot be promoted without root-stability and OOS incremental-value tests."
    covers: [REQ-EXP-013, REQ-NRT-F]
  - item: 16
    text: "Adaptive stop proposals are immutable and point-in-time causal."
    covers: [REQ-WP-020, REQ-WP-032]
  - item: 17
    text: "Default stop policy never widens accepted position risk."
    covers: [REQ-WP-033]
  - item: 18
    text: "Stop-policy reports include premature-stop rate, MFE give-back and realized R versus naive trailing baselines."
    covers: [REQ-EXP-017, REQ-WP-034]
  - item: 19
    text: "Adaptive stop management can run entirely in shadow/paper mode without trading credentials."
    covers: [REQ-WP-020, REQ-WP-072]
---

## Requirement

PRD §47 is the only place the PRD says what finishing means, and it opens by
saying what it does not mean:

> The project is not "done" merely because a chart and bot exist.

Nineteen conditions follow. They are quoted verbatim in the `conditions:`
frontmatter above, each beside the requirements that deliver it.

**Why this note exists.** Every one of the nineteen already had delivery behind
it before this note was written — but the mapping lived nowhere. It was
reconstructed by hand, by reading 103 requirement titles and grepping the source,
and a mapping assembled that way is a claim about a moment. The next requirement
to change one of those areas would not know it was answering §47, and nothing
would notice when an answer stopped being true.

This is the same shape as three gaps already closed by this project. §34 held
seven requirements that were satisfied only because the code that could violate
them did not exist yet ([[REQ-WP-072]]). §35.3 and §35.4 held correctness tests
that nothing enumerated ([[REQ-NRT-REPAINT]], [[REQ-NRT-LEAK]]). §47 is the
largest of them: it is the definition of done, and nothing checked it.

**What it is not.** It is not new delivery. Nothing here builds anything; it
records what delivers what, so a machine can answer "is this done" instead of a
person answering "I looked, and I think so".

## Acceptance

- Every one of the nineteen conditions carries at least one covering
  requirement. A condition with an empty list fails, naming the item number and
  quoting its text.
- Every requirement named anywhere in `conditions:` exists, and has reached
  `implemented`. A condition whose covering work is still `planned` makes §47
  unmet, by name.
- The flat `covers:` list is exactly the union of the per-condition lists —
  checked, not maintained in parallel. Two lists that can disagree will.
- The nineteen items and their text match PRD §47 verbatim, line for line. A
  condition reworded into something easier to satisfy fails against the PRD
  itself.
- The count is asserted. Nineteen conditions, so a note that lost one cannot
  report that the rest are met.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-115-definition-of-done]]
- **Tests:**
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_whose_work_is_finished_is_not_named[implemented]`
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_whose_work_is_finished_is_not_named[verified]`
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_whose_work_is_unfinished_is_named[draft]`
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_whose_work_is_unfinished_is_named[planned]`
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_whose_work_is_unfinished_is_named[specified]`
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_whose_work_is_unfinished_is_named[tested]`
    - `tests/tools/trace/test_definition_of_done.py::test_a_condition_with_no_covering_requirement_is_named`
    - `tests/tools/trace/test_definition_of_done.py::test_a_covering_requirement_that_does_not_exist_is_refused`
    - `tests/tools/trace/test_definition_of_done.py::test_a_note_that_lost_a_condition_is_refused`
    - `tests/tools/trace/test_definition_of_done.py::test_a_prd_that_states_no_conditions_is_refused`
    - `tests/tools/trace/test_definition_of_done.py::test_a_prd_with_no_section_48_is_refused`
    - `tests/tools/trace/test_definition_of_done.py::test_a_reworded_condition_fails_against_the_prd`
    - `tests/tools/trace/test_definition_of_done.py::test_an_unknown_status_is_refused_separately_from_a_missing_note`
    - `tests/tools/trace/test_definition_of_done.py::test_every_condition_is_quoted_verbatim_from_the_prd`
    - `tests/tools/trace/test_definition_of_done.py::test_every_covering_requirement_has_been_delivered`
    - `tests/tools/trace/test_definition_of_done.py::test_no_condition_is_unclaimed`
    - `tests/tools/trace/test_definition_of_done.py::test_the_flat_covers_list_is_exactly_the_union`
    - `tests/tools/trace/test_definition_of_done.py::test_the_items_are_numbered_one_to_nineteen`
    - `tests/tools/trace/test_definition_of_done.py::test_the_mapping_reaches_more_than_a_handful_of_requirements`
    - `tests/tools/trace/test_definition_of_done.py::test_the_prd_still_states_nineteen_conditions`
    - `tests/tools/trace/test_definition_of_done.py::test_the_two_lists_are_compared_in_both_directions`
- **Code:**
    - `tools/trace/definition_of_done.py`
- **Outcomes:** [[OUT-2026-09-17-implement-definition-of-done]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
