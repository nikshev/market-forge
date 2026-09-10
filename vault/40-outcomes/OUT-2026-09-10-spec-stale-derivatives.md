---
id: OUT-2026-09-10-spec-stale-derivatives
step: spec
records: [REQ-WP-026]
commit: null
---

## What was done

`specs/064-stale-derivatives/spec.md`: three user stories, 9 functional
requirements, 6 success criteria. [[REQ-WP-026]] moves to `specified`.

## What was decided

- **Refusal, not exclusion.** `crossvenue` excludes a stale quote because it has
  others to fall back on. A single state has nothing to fall back to.
- **A stale refusal is a different type from an absent one.** A venue that never
  published and one that stopped are different facts — the same distinction three
  other requirements here have had to make explicit.
- **The z-score's history is untouched.** A staleness rule applied to the window
  rather than to the reading would refuse the feature exactly when it has most to
  say, and it would look like the rule working.
- **The boundary is inclusive and stated.** "Older than the tolerance" has two
  readings; a boundary left to the implementation changes when someone refactors.
- **Age is measured from the event time.** A correction arriving late describes an
  old instant and is old.

## What is still open

- **Existing callers will break**, and the spec calls that a finding rather than
  a cost: a fixture holding a state older than any sensible tolerance was
  asserting on a value the criterion says must not be used. How many there are is
  not known until the default is chosen.
- **A default that is right for funding may be wrong for open interest.** Both
  poll on their own cadence, and one tolerance for the package may turn out to be
  one too few — visible only once a caller sets one.
