---
id: OUT-2026-09-10-spec-outage-alerts
step: spec
records: [REQ-WP-035]
commit: null
---

## What was done

`specs/073-outage-alerts/spec.md`: four user stories, 11 functional
requirements, 7 success criteria. [[REQ-WP-035]] moves to `specified`.

## What was decided

- **FR-002 and FR-003 are the same rule at two scales**, and they are the
  sharpest form of "absent is not zero" this repository has met. Nothing
  reported is not good news; one metric not reported is not one metric within
  its limit. The failure they guard against — a feed so broken it cannot even
  report — is exactly the failure the alerting exists for, and a default of GOOD
  is precisely what would silence it.
- **FR-007 is two rules because neither follows from FR-005.** A feed first seen
  in a bad state alerts: waiting for a prior good state stays silent through an
  outage that began before the process did. A feed first seen as GOOD does not:
  announcing a recovery from nothing reports an outage that never happened.
- **Four states stay four.** §32's eligibility rules sit directly beneath its
  state list and treat DEGRADED and STALE differently, so collapsing them makes
  the rules above unimplementable while looking like a simplification.
- **Four of §32's nine metrics are deliberately not modelled.** Chain RPC lag,
  subgraph indexing lag and insert delay belong to systems that do not exist
  here, and a field for one of them would suggest something watches it.

## What is still open

- **Nothing produces a health reading.** No connector runs; nothing counts a
  reconnect or a gap.
- **Whether a DEGRADED feed escalates on duration alone.** An hour degraded is
  arguably a different fact from a second degraded, and nothing here says so.
- **Where §32's eligibility rules live.** They are stated in the PRD and no
  signal path consumes a health state.
