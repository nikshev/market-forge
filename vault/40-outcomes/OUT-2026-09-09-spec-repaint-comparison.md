---
id: OUT-2026-09-09-spec-repaint-comparison
step: spec
records: [REQ-US-003]
commit: null
---

## What was done

`specs/028-repaint-comparison/spec.md`: two user stories, 11 functional
requirements, 7 success criteria.

## What was decided

- **The refit must see later bars** ([[ADR-046]]). Reading §27.5 against the
  code showed the existing `CURRENT REFIT` caps at the requested instant, so
  today's toggle measures model drift rather than repaint. Both questions are
  legitimate; only one is REQ-US-003's.
- **`now_ns` is an argument, not a clock.** §27.5 refits over "visible/current
  history", and what is visible belongs to the reader.
- **The width-relative delta is the comparable number.** A hundred dollars of
  repaint means one thing on a five-hundred-wide channel and another on a
  five-wide one.
- **A version difference is reported, not refused.** Refusing would hide the
  drift that only shows up across versions.

## What is still open

- **No chart view of the comparison.** REQ-US-003 asks that the snapshot be
  "available for comparison"; the two chart modes already exist for looking at
  one at a time.
