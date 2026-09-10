---
id: OUT-2026-09-10-requirement-stale-derivatives
step: requirement
records: [REQ-WP-026]
commit: null
---

## What was done

[[REQ-WP-026]] extracted from PRD §45's Phase 3 acceptance, the second of its
two criteria: "stale REST polling cannot silently reuse old value".

## What was decided

- **The criterion is not met, and that is checkable rather than an opinion.**
  `state_at` returns the newest state at or before the instant with no upper
  bound on its age, so a funding rate from a day ago is returned exactly as a
  fresh one. The first criterion — point-in-time safety — does hold.
- **The gap is specific to the package the criterion names.** `crossvenue`
  excludes a quote past its tolerance and says why; `book` and `alerting` guard
  it; PRD §43's ranker penalizes it. `derivatives` is the one without it, and it
  is the REST-polled data the criterion is about.
- **A maximum age is configuration, not a magic number.** Principle X asks for
  the caller to set it. What it must not be is absent, because absent means
  infinite, and infinite makes the criterion vacuous.
- **The z-score window is untouched.** `funding_z` looks back over many
  observations by design; refusing old *history* would break the feature the
  rule is meant to protect. What is refused is a stale reading presented as the
  value now.

## What is still open

- **How many existing tests hold states older than any sensible tolerance** is
  unknown until a default is chosen. A default that breaks a dozen fixtures is
  not by itself an argument against the default.
- **Refusal or exclusion** is the shape question. `crossvenue` excludes and
  names; `state_at` returns one state, so it has nothing to exclude *to* —
  which points at refusal, and refusal changes every caller.

## How this was found

While sizing Phase 3's other open deliverable, "optional long/short stats". The
visit produced something better than the optional feature: an acceptance
criterion the phase already states and the code does not meet.
