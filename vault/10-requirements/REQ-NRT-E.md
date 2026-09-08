---
id: REQ-NRT-E
title: replay parity
type: constraint
hard_gated: true
prd_ref: "Test E — replay parity"
prd_lines: "2244-2247"
phase: null
status: implemented
depends_on: []
tags: []
---

## Requirement

Live recorded outputs and deterministic replay outputs must match for the same event stream/config/model artifact.

## Acceptance

- live recorded outputs and deterministic replay outputs match for the same event stream, config, and model artifact.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-014-turning-points]]
- **Tests:**
    - `tests/unit/extrema/test_non_repainting.py::test_e_a_different_configuration_gives_a_different_answer`
    - `tests/unit/extrema/test_non_repainting.py::test_e_a_replayed_stream_matches_the_live_run_exactly`
    - `tests/unit/extrema/test_non_repainting.py::test_e_feeding_one_bar_at_a_time_matches_feeding_the_whole_series`
- **Code:**
    - `src/channelflow/extrema/detector.py`
- **Outcomes:** [[OUT-2026-09-08-implement-turning-points]], [[OUT-2026-09-08-plan-turning-points]], [[OUT-2026-09-08-spec-turning-points]], [[OUT-2026-09-08-tasks-turning-points]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
