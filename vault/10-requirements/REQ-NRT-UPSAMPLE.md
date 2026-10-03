---
id: REQ-NRT-UPSAMPLE
title: No unfinalized higher-timeframe close reaches a lower-timeframe consumer
type: constraint
prd_ref: "§13A.17"
prd_lines: "1853-1875"
phase: null
status: implemented
depends_on: [REQ-WP-073]
tags: [timeframes, non-repainting]
hard_gated: true
---

## Requirement

PRD §13A.17's closing sentence, quoted verbatim:

> Do not upsample a higher-timeframe future close into lower-timeframe features
> before that higher-timeframe bar is finalized.

The section it closes is about extrema: "Extrema should be computed
independently on each timeframe and optionally linked", with an example that
ends "This is not equivalent to a 1h top", and a list of five optional
confluence features. **That subject is not this note.** §13A.17's extrema
hierarchy and its confluence features have no requirement note yet; this one
extracts only the prohibition, which is the part that binds any component
producing or consuming bars at more than one timeframe.

**The token is a word, not a letter**, for the reason [[REQ-NRT-REPAINT]] gives:
`A`–`F` are §13A.28's own six named tests, and lettering this one would claim
that section has a seventh.

### What this forbids that nothing else already forbids

Three rules in this repository sound like this one and are not it:

- The `bars` table already refuses an unfinalized row — "a canonical table
  holding an unfinalized bar would hold a row that is still going to change"
  ([[ADR-005]], `src/channelflow/tables/bars.py`). That governs **writing**.
- [[REQ-NRT-LEAK]] (§35.4) demands a feature give the same value on a truncated
  and a full dataset. That governs **one feature's own computation**.
- Constitution Principle I forbids look-ahead generally.

This one governs the **seam between two timeframes**: a 1h bar that has not
closed at `t` must not reach anything computed at `t`, however it travelled
there. A resampler that emits a partial window produces a row that satisfies
every rule above at the moment it is written and is still a future close handed
backwards.

### Why a resampler makes this urgent

A higher timeframe assembled from stored one-minute bars has a failure the
trade-driven `BarBuilder` does not: its input can be **incomplete without being
late**. `BarBuilder` sees a trade stream and closes a window when its watermark
passes; a resampler sees rows, and a window missing three of its 240 minutes
looks exactly like a window that has all of them unless something counts. A bar
computed from what happened to be there is wrong in a way no downstream reader
can detect.

## Acceptance

- A higher-timeframe bar covering `[s, s + T)` is published only once every
  constituent source bar in that window is present and final. A window with a
  missing source bar yields **no bar**, not a bar computed from the rest.
- An incomplete window is **refused with a reason that names the window and what
  was missing**, and the refusal is visible to the caller rather than logged and
  swallowed. A silent skip and a correct bar are indistinguishable to a reader,
  which is the failure this exists to prevent.
- Asking for the `T` bar as of any instant strictly inside `[s, s + T)` returns
  nothing for that window. Proven by asking, not by inspecting `close_time_ns`.
- A consumer computing at `t` never reads a higher-timeframe bar whose
  `close_time_ns` is greater than `t`.
- A deliberately leaking resampler — one that emits the window in progress — is
  caught by the suite and **named**, proven by introducing one. A constraint
  whose test has never seen the violation it forbids is a constraint nobody has
  checked.
- The suite runs in CI with no services and no network.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-125-no-unfinalized-upsample]]
- **Tests:**
    - `tests/unit/test_upsample_seam.py::test_a_bar_cannot_be_read_as_of_any_instant_inside_its_window`
    - `tests/unit/test_upsample_seam.py::test_a_complete_window_of_final_minutes_is_a_bar`
    - `tests/unit/test_upsample_seam.py::test_a_missing_minute_is_still_refused_with_the_window_and_the_count`
    - `tests/unit/test_upsample_seam.py::test_a_refusal_names_a_few_minutes_and_counts_the_rest`
    - `tests/unit/test_upsample_seam.py::test_a_repeated_minute_does_not_stand_in_for_a_missing_one`
    - `tests/unit/test_upsample_seam.py::test_a_window_still_open_yields_neither_a_bar_nor_a_refusal`
    - `tests/unit/test_upsample_seam.py::test_a_window_whose_minutes_are_all_there_but_one_repeated_is_refused`
    - `tests/unit/test_upsample_seam.py::test_a_window_with_a_source_bar_that_is_not_final_is_refused_and_says_which`
    - `tests/unit/test_upsample_seam.py::test_no_read_as_of_t_contains_a_bar_that_closes_after_t`
    - `tests/unit/test_upsample_seam.py::test_of_the_five_window_shapes_exactly_one_is_a_bar_and_exactly_three_are_refused`
    - `tests/unit/test_upsample_seam.py::test_the_bar_is_readable_the_instant_its_window_closes`
    - `tests/unit/test_upsample_seam.py::test_the_property_is_the_as_of_reads_and_not_an_accident_of_the_fixture`
- **Code:**
    - `src/channelflow/pipeline/resample.py`
- **Outcomes:** [[OUT-2026-10-03-implement-no-unfinalized-upsample]], [[OUT-2026-10-03-plan-no-unfinalized-upsample]], [[OUT-2026-10-03-spec-no-unfinalized-upsample]], [[OUT-2026-10-03-tasks-no-unfinalized-upsample]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

### 2026-10-03: what the first test of this found

[[REQ-WP-073]] was `implemented` and its resampler "refused incomplete windows", with a test. Running
it for this requirement showed it judged completeness by **counting** bars: minutes 0, 1, 2, 3 and 3
again were folded into a bar although minute 4 was missing, and so was a window holding a source bar
that was not final. Neither occurs on the deployment (no duplicate row, and the table refuses
unfinalized ones on write), which is why nothing had seen them: what kept them out was another
module's behaviour. The resampler now identifies the minutes; a differential over 18,026 live
windows shows no change in what it produces today. The "consumer" the requirement speaks of does not
yet exist (§13A.17's extrema hierarchy and confluence features have no note), so the guarantee is
stated and tested on the as-of read, which whatever is written later will inherit.
