---
id: OUT-2026-09-10-plan-stale-derivatives
step: plan
records: [REQ-WP-026]
commit: null
---

## What was done

`specs/064-stale-derivatives/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/freshness.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-026]] moves to `planned`.

## The finding that changed the plan

The spec's FR-007 assumed every feature would inherit the rule through the
package's shared point-in-time path. **There is no shared path.** `state_at` was
written as that seam and its own docstring argues for it — "a rule each call site
has to remember is a rule one call site will forget" — and no feature ever called
it. Funding filters on `next_funding_time_ns`, open interest builds its own
series.

A staleness rule placed only in `state_at` would have protected nothing while
looking exactly like the criterion being met. The rule went into a free function
that each reader calls, and the docstring records why it cannot be a method on a
seam nobody uses.

## What was decided

- **A free function, called from three places.** The readers find their newest
  observation differently — the latest state, the last settled interval, the last
  open-interest point — and only the age is shared.
- **Existing tests pass an explicit `NOT_ABOUT_FRESHNESS`.** Fifteen failed on
  the new default and every one was about something else. Saying so out loud
  beats the previous state, where a test passed because its fixture happened to
  sit inside a window it never meant to be inside.
- **Nothing settled is no value, not a stale one.** A venue that has published
  states but settled no funding interval has nothing to be stale about.

## What is still open

- **The next reader has to remember.** That is the honest cost of there being no
  seam, and nothing enforces it.
