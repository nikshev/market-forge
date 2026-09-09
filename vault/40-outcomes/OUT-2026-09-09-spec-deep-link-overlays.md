---
id: OUT-2026-09-09-spec-deep-link-overlays
step: spec
records: [REQ-US-002]
commit: null
---

## What was done

`specs/027-deep-link-overlays/spec.md`: two user stories, 10 functional
requirements, 7 success criteria.

## What was decided

- **"Exactly the signal's timestamp" is a visible range, not a marker.** The
  chart already drew a marker at the instant and then fitted the view to five
  hundred bars — technically containing the moment and leaving the reader to
  find it.
- **A partly-readable overlay list is discarded whole** ([[ADR-045]]).
- **An empty list is a recorded fact**, not an absence.
- **The vocabulary is the PRD's full twelve** even though the chart draws six,
  so a link written now stays valid as layers are added.

## What is still open

- **The pipeline does not populate `Alert.overlays` yet.** Alerts sent today
  land in the "not recorded" state, which is stated on the page rather than
  hidden.
