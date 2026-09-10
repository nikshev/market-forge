---
id: OUT-2026-09-10-implement-stale-derivatives
step: implement
records: [REQ-WP-026]
commit: null
---

## What was done

`require_fresh`, `StaleState` and `DEFAULT_STALENESS_NS` in
`derivatives/state.py`, called from `state_at`, `settled_funding` and
`oi_series`. PRD §45's Phase 3 second acceptance criterion is met.

11 new tests, 1602 in the suite, mypy clean at 168 files, 10 of 10 mutants
caught.

## What the mutation sweep found

Three survivors, all real:

- **A negative tolerance was guarded twice.** The copy in `state_at` raised the
  same error with the same words one frame up, so deleting either changed
  nothing. Removed; `require_fresh` owns the rule.
- **The default was tested as finite, not as sensible.** A thirty-year default
  passed every assertion — finite, positive, and just as vacuous as none. The
  test now asserts it is at most an hour, which is the claim the default actually
  makes.
- **Open interest was never exercised.** Funding and open interest are polled
  separately and read separately, and no shared path covers the second for free —
  which is the same finding the plan step made, showing up again in the tests.

## What is still open

- **The next reader of polled state has to remember to call `require_fresh`.**
  That is the honest cost of there being no seam, and nothing enforces it. A
  mechanical check — every module in `derivatives/` that reads `at_ns` calls it —
  is possible and was not written, because it would have been a fourth guard
  invented in the same session as the first three.
- **One tolerance may be one too few.** Funding settles every eight hours on most
  venues while open interest polls every minute; a single default serves both
  only because callers can override it. The first caller who sets two different
  values will make that visible.
- **Liquidations are untouched.** They arrive on a stream rather than by polling,
  so the criterion does not name them — but a stream that stops is just as silent
  as a poll that fails, and nothing here says what that should do.
