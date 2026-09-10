---
id: OUT-2026-09-10-spec-long-short
step: spec
records: [REQ-WP-031]
commit: null
---

## What was done

`specs/069-long-short/spec.md`: three user stories, 9 functional requirements,
7 success criteria. [[REQ-WP-031]] moves to `specified`.

## What was decided

- **"Optional" is the thing to guard against.** It describes the venue and
  invites a reading where the feature may be casual. A sometimes-absent field is
  precisely where an absent value quietly becoming neutral does the most damage,
  because no consumer will ever see a gap to be suspicious of.
- **FR-002 and the first edge case say one rule twice, on purpose** — once as a
  requirement, once as the concrete value that would collapse it. 1.0 is the
  default an implementation reaches for.
- **Crowding is relative or it is not context.** A spec asking only for the ratio
  would be satisfied by exposing a number, and the PRD asked for context.
- **The z-score is reused, not described.** Two implementations of "too few
  observations" would drift invisibly, because both would return numbers.
- **Two ratios, never averaged.** A global account ratio and a top-trader
  position ratio measure different populations; their average describes neither.

## What is still open

- **Nothing writes positioning**, as nothing writes the other derivative
  features. This adds the state and the readings; filling them belongs to the
  derivatives path.
- **Which venue field feeds which ratio** is the connector's, and this
  specification deliberately does not decide it.
