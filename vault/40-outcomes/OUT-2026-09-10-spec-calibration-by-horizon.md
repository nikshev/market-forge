---
id: OUT-2026-09-10-spec-calibration-by-horizon
step: spec
records: [REQ-WP-023]
commit: null
---

## What was done

`specs/062-calibration-by-horizon/spec.md`: three user stories, 8 functional
requirements, 6 success criteria. [[REQ-WP-023]] moves to `specified`.

## What was decided

- **A thin slice reports its count and no curve.** A slice with three rows that
  reported a curve would reintroduce, one level down, the exact defect slicing
  removes — an average speaking for something that cannot speak for itself.
- **A target that never occurs at a horizon is measured, not unmeasured.** It has
  observations and no positive outcomes, which is a real calibration. An
  implementation keying on "no positives" rather than "too few rows" would merge
  the two, and the edge case is written down because that is the likely mistake.
- **The minimum is the caller's.** Principle X, and §23.8 gives no number, so a
  constant inside the reporter would be a threshold nobody could change.
- **Horizons are grouped exactly.** Labels carry a stated `H`, so rows share
  exact horizons; bucketing would add a second arbitrary choice on top of the
  minimum.
- **The pooled figure stays, beside the slices.** Removing it breaks callers for
  no gain; replacing the slices with it is the defect being fixed.

## What is still open

- **Whether exact grouping survives a labeller that varies `H` per row** is not
  known. Nothing does that today. If one arrives, the slices become one per row
  and the report says nothing — which would be visible rather than silent, but it
  would still be useless.
