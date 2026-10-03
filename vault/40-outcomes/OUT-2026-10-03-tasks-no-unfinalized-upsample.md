---
id: OUT-2026-10-03-tasks-no-unfinalized-upsample
step: tasks
records: [REQ-NRT-UPSAMPLE]
commit: null
---

## What was done

Broke the plan into 13 tasks in seven phases, then ran the analysis of `spec.md`, `plan.md` and
`tasks.md` against each other. Every FR and SC maps to at least one task (the coverage table is in
`tasks.md`); the analysis found three things, each resolved before this commit.

## What was decided

**The analysis found, and what was done:**

- **The spec promised more than the test does.** User Story 3 said "for every minute `t` of the
  day" and SC-002 "zero for every `t`"; the drafted test reads at every seventh minute plus the
  instant before, at and after every window boundary of every configured timeframe up to a day. The
  claim was the strong one and the evidence the sampled one. The spec was reworded to name the
  instants — and to say why: a leak shows at a boundary, and every minute is 1,440 reads for no extra
  evidence. The test was not changed to fit; the sentence was, because the sentence was the one that
  had not been measured.
- **The drafted tests lived only in the session's scratch space.** They are now committed under
  `specs/125-no-unfinalized-upsample/red/` with their RED run, outside `tests/` (testpaths is
  `tests`, so the gate does not collect them) until T002 moves them in. Without that the tasks would
  have pointed at a path that disappears with the session.
- **Deploying this change would have broken another requirement's measurement.** The shared image
  rebuild recreates every service; [[REQ-WP-079]]'s acceptance is a 24-hour run from 07:18 UTC on
  2026-10-03 and asks that `resample` not have restarted. T013 therefore defers the deployment until
  that check is done, and says why. It is not a precondition: this requirement's own acceptance asks
  for a suite with no services and no network.

**Also decided.** T005 is a differential check on real data — the old and new `resample` over every
live one-minute series — because the claim that the change alters nothing on the deployment is the
one most worth testing and is cheap to test. A difference would be a finding, not noise.

## What is still open

- Whether the suite can be brought under 60 seconds without thinning the instants (T007). If it
  cannot, the spec's SC-004 changes, with the reason.
- Whether any mutation survives (T009–T010). A survivor in the `bars` schema's as-of column would
  mean the seam's own storage filter is untested, and is not acceptable.
