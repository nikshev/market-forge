---
id: OUT-2026-09-10-plan-outage-alerts
step: plan
records: [REQ-WP-035]
commit: null
---

## What was done

`specs/073-outage-alerts/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/health.md`, `quickstart.md`. [[REQ-WP-035]] moves to `planned`.

## What was decided

- **"Nothing reported" reuses INVALID rather than adding a fifth state.** A
  state the PRD does not name would have to be threaded through §32's
  eligibility rules, which name four, and every consumer would need a rule the
  PRD never gives. The reason string carries what a state name would only
  approximate: invalid because gappy against invalid because silent.
- **The states are ranked, and the rank gets its own test.** "The worst decides"
  is then a comparison rather than a conditional chain a tenth metric would have
  to be threaded through. A mis-ordered rank makes a stale feed outrank an
  invalid one and every assessment still returns a plausible state — which is
  why the ordering is asserted directly rather than implied by the tests that
  use it.
- **The state model lives outside `alerting`.** §32's states are consumed by
  signal eligibility, which is not an alerting concern; under the notifier,
  every future consumer would import the alerting package to ask whether a feed
  is trustworthy.
- **No clock.** Both instants are arguments and a duration is their difference,
  so a replay produces the same message ([[ADR-018]]).

## What is still open

- Nothing new. The three from [[OUT-2026-09-10-spec-outage-alerts]] stand.
