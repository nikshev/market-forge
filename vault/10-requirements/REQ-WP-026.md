---
id: REQ-WP-026
title: A stale derivatives state is refused, not returned as current
type: work-package
prd_ref: "§45 Phase 3 acceptance, §16, §19"
prd_lines: "6771-6774"
phase: 3
status: implemented
depends_on: [REQ-WP-013]
tags: []
---

## Requirement

PRD §45's Phase 3 states two acceptance criteria, and this is the second:

    - all derivative features point-in-time safe;
    - stale REST polling cannot silently reuse old value.

The first holds: `state_at` never returns a state later than the instant asked
about. **The second does not.** `state_at` returns the newest state at or before
`at_ns` with no upper bound on its age, so a funding rate from an hour ago — or
a day ago — is returned exactly as a fresh one, and every feature built on it
reports a number that looks current.

Derivatives state is the REST-polled data this criterion is about. Funding, open
interest and basis arrive by polling; a poll that failed, or a venue that stopped
publishing, leaves the last value in place and nothing downstream can tell.

Staleness is handled elsewhere in the repository — `crossvenue` excludes a quote
past its tolerance and names why, `book` and `alerting` both guard it, and PRD
§43's ranker penalizes it. The one package the acceptance criterion names is the
one without it.

## Acceptance

- reading state at an instant takes a maximum age, and a state older than it is
  refused with its age and the tolerance named;
- the tolerance is the caller's, with a stated default rather than a hidden one;
- a refusal is distinguishable from "no state at all": a venue that never
  published and one that stopped are different facts;
- every feature derived from state inherits the refusal rather than re-checking
  it, so a new feature cannot forget;
- a z-score window may still span older observations — the rule is about the
  value being read as current, not about the history behind it.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-064-stale-derivatives]]
- **Tests:**
    - `tests/unit/derivatives/test_staleness.py::test_a_feature_inherits_the_refusal_without_re_checking_it`
    - `tests/unit/derivatives/test_staleness.py::test_a_feature_with_nothing_settled_reports_nothing_rather_than_stale`
    - `tests/unit/derivatives/test_staleness.py::test_a_negative_tolerance_is_refused`
    - `tests/unit/derivatives/test_staleness.py::test_a_stale_state_and_no_state_are_different_refusals`
    - `tests/unit/derivatives/test_staleness.py::test_a_state_exactly_at_the_tolerance_is_fresh`
    - `tests/unit/derivatives/test_staleness.py::test_a_state_older_than_the_tolerance_is_refused`
    - `tests/unit/derivatives/test_staleness.py::test_a_state_within_the_tolerance_is_returned`
    - `tests/unit/derivatives/test_staleness.py::test_a_z_score_still_reads_the_history_behind_a_fresh_value`
    - `tests/unit/derivatives/test_staleness.py::test_open_interest_refuses_a_stale_reading_too`
    - `tests/unit/derivatives/test_staleness.py::test_the_default_tolerance_is_about_polling_not_merely_finite`
    - `tests/unit/derivatives/test_staleness.py::test_which_state_wins_at_one_instant_is_unchanged`
- **Code:**
    - `src/channelflow/derivatives/funding.py`
    - `src/channelflow/derivatives/openinterest.py`
    - `src/channelflow/derivatives/state.py`
- **Outcomes:** [[OUT-2026-09-10-implement-stale-derivatives]], [[OUT-2026-09-10-plan-stale-derivatives]], [[OUT-2026-09-10-requirement-stale-derivatives]], [[OUT-2026-09-10-spec-stale-derivatives]]
<!-- trace:end -->

## Notes

Found while sizing Phase 3's other open deliverable. The `not_delivered` entry
that led here was "optional long/short stats", and this is the more useful half
of that visit: an optional feature nobody has asked for, against an acceptance
criterion the phase already states and the code does not meet.

**Why a maximum age is not a threshold in the pejorative sense.** Principle X
asks for thresholds to be configuration, and this one is: a caller sets it. What
it must not be is absent, because absent means infinite — and infinite is the
one value that makes the criterion vacuous.

**The z-score window is deliberately untouched.** `funding_z` looks back over
many observations by design; a rule that refused old *history* would break the
feature it is meant to protect. What is refused is a stale reading presented as
the value now.
