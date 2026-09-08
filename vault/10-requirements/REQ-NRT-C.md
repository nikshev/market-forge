---
id: REQ-NRT-C
title: confirmation legality
type: constraint
hard_gated: true
prd_ref: "Test C — confirmation legality"
prd_lines: "2232-2239"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

```text
known_at >= extremum_time
```

and the confirmation logic must not read events with `available_at > known_at`.

## Acceptance

- `known_at >= extremum_time` holds for every confirmed extremum;
- confirmation logic never reads events with `available_at > known_at`.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Tests:**
    - `tests/unit/extrema/test_directional_change.py::test_a_high_is_dated_to_its_peak_and_known_at_the_crossing`
    - `tests/unit/extrema/test_directional_change.py::test_a_record_claiming_to_be_known_before_it_happened_cannot_be_built`
    - `tests/unit/extrema/test_directional_change.py::test_known_at_is_never_before_extremum_time_over_a_long_series`
    - `tests/unit/extrema/test_non_repainting.py::test_c_known_at_is_never_before_the_extremum`
    - `tests/unit/extrema/test_non_repainting.py::test_c_no_confirmation_reads_a_bar_later_than_its_known_at`
- **Code:**
    - `src/channelflow/extrema/detector.py`
    - `src/channelflow/extrema/models.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-points]], [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
