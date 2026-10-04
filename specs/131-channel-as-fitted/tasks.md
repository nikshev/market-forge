---
description: "Tasks for REQ-WP-082 — the chart draws the channel as the model fitted it"
---

# Tasks: The chart draws the channel as the model fitted it

**Tests** first, run RED. Python marker `@pytest.mark.trace("REQ-WP-082")`; web files `// @trace: REQ-WP-082`.

- [ ] T001 Record the **before**: the live channel for BTCUSDT 15m; that every candle gets the same value (`series.ts` `at()`); the width of the channel against the axis
- [ ] T002 Write `tests/unit/api/test_channel_slope.py` (pytest): the stored slope is served in the stored and the refit mode; every earlier field unchanged. RED: `KeyError: 'slope_log_per_bar'`
- [ ] T003 Write `apps/web/src/__tests__/channelWindow.test.ts` (vitest): L points ending at the last bar closing at or before `as_of`; last = `_now`, first = `_now·exp(−(L−1)·s)`; constant ratios; an earlier `as_of`; fewer bars than L; a non-finite slope draws nothing; `visibleRangeForChannel`; the style constants. Replace the old whole-history assertion in `Chart.test.tsx`. RED, recorded
- [ ] T004 Add `slope_log_per_bar` to `ChannelOut` and `.of`; add it to `types.ts`; rewrite the channel lines in `series.ts`; add `visibleRangeForChannel`; use it and the new style in `Chart.tsx`. `@trace: REQ-WP-082` in each
- [ ] T005 Run the new tests and the existing API and web tests: only the one assertion that encoded the fault changes
- [ ] T006 **Check the reconstruction against live data (SC-002):** for BTCUSDT 15m at several instants, fraction of the window's closes inside the drawn band (expect about 0.8); record
- [ ] T007 `make lint typecheck test web-typecheck web-test web-build`; rebuild and recreate `api` and `web` only (`--no-deps`)
- [ ] T008 Write the implement outcome note; set `implemented`; `make graph && make validate`; commit

## Coverage

| requirement | task |
|---|---|
| FR-001 slope served | T002, T004 |
| FR-002 window only, ending at `as_of` | T003, T004 |
| FR-003 the formula | T003 |
| FR-004 no usable slope, no lines | T003 |
| FR-005 the default view | T003, T004 |
| FR-006 legible | T003 |
| FR-007 nothing else changes | T005 |
| SC-001 exact values | T003 |
| SC-002 against live data | T006 |
| SC-003 the view | T003 |
