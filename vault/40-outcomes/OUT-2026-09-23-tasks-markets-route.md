---
id: OUT-2026-09-23-tasks-markets-route
step: tasks
records: [REQ-WP-075]
commit: null
---

## What was done

`specs/120-markets-route/tasks.md` generated and analysed against `spec.md`
and `plan.md`: 17 tasks in seven phases.

| phase | tasks | delivers |
|---|---|---|
| Setup | T001 | the baseline: `/markets` shows the placeholder today |
| Foundational | T002–T006 | `MarketOut`, `fetchMarkets`, `marketHref`, `scoreLabel` |
| US1 (P1) | T007–T008 | the list, in the API's order, unscored as unscored, empty≠failed |
| US2 (P1) | T009–T010 | rows as links to the deep link at the chosen `tf` |
| US3 (P2) | T011–T012 | `/` and `/markets` render the view; unknown paths keep the placeholder |
| US4 (P2) | T013–T014 | options from the API; a control failure does not take the rows down |
| Polish | T015–T017 | docs, the running stack, the gates |

## What the analysis found, and how it was resolved

**SC-004 needed a sharper assertion.** "An unseen set renders" proves the view
does not *need* a list; it does not prove one is absent. A hard-coded fallback
would render the unseen set correctly and appear only when the offered read
fails. T013 was tightened on both sides: the option list must equal exactly
what the API served (an extra fallback entry fails), and a failed offered read
must offer **no** options (a fallback renders where nothing should).

**The test/implementation pairs listed implementation first**, as in
[[REQ-WP-073]] and [[REQ-WP-074]]. A note now states that the test task runs
first in every pair, so the list does not read as implementation preceding its
test.

Nothing else: no duplication, no ambiguity, no terminology drift, every FR and
SC mapped, no constitution conflict, and no unmapped task (Setup and Polish are
cross-cutting).

## Metrics after resolution

- Requirements: 7 FR + 5 SC = 12; coverage 12/12 (100%).
- Tasks: 17, of which 6 are test tasks and 6 are `[P]`-able test files.
- Critical: 0. High: 0. Medium: 1 (resolved). Low: 1 (resolved).
- Ambiguity: 0. Duplication: 0. Unmapped tasks: none.

## What is still open

- **No backend task**: §28.1's read is used as it stands. If the markets table
  is empty on the running stack, the view must read "no markets" and T016
  records which state was actually measured — an empty deployment is a fact,
  not a blocker.
- **The web gates remain CI-only** (ADR-021); T017 runs them locally as
  [[REQ-WP-074]]'s T035 did.
