---
id: OUT-2026-09-23-tasks-chart-timeframe-control
step: tasks
records: [REQ-WP-074]
commit: null
---

## What was done

`specs/119-chart-timeframe-control/tasks.md` generated and analysed against
`spec.md` and `plan.md`: 36 tasks in seven phases.

| phase | tasks | delivers |
|---|---|---|
| Setup | T001 | the baseline recorded (constant `15 * MINUTE_NS`, `App.tsx:62`) |
| Foundational | T002–T015 | `offered()`, `Settings.timeframes`, the route and schemas, compose env, `timeframes.ts`, `fetchTimeframes` |
| US1 (P1) | T016–T020 | the control and the four requests at the in-force duration; stale-response guard |
| US2 (P1) | T021–T026 | the link as initial value, the one default, refusal instead of substitution |
| US3 (P2) | T027–T030 | `replaceState` for timeframe and mode, other link parameters preserved |
| US4 (P2) | T031–T032 | the control renders what the API reported; no token list in the frontend |
| Polish | T033–T035 | docs, quickstart against the stack, the gates |

## What the analysis found, and how it was resolved

**FR-011 had no task.** "Empty reads as empty, failed as failed" is existing
behaviour, and T019 rewrites the request path it lives in — a regression task
was missing, not a RED one. Added as **T019a**, phrased as a regression test
with the reason it has no failing-first step, so the omission is repaired
without recording a failure that did not happen.

**"No request before the offered set arrives" was implied, not asserted.**
T019 implements it; nothing pinned it. Added to **T016**'s assertion list: a
request issued at a guessed duration is precisely the defect the feature
removes, so its absence deserves a line in the test that would notice.

**The default-missing case was covered only by implication.** The spec's edge
case says a deployment that configures the default away refuses it like any
other token; T024 covered unoffered tokens generally. Naming the default
explicitly was added, because "silently chose a neighbour" is the failure the
sentence exists to forbid.

**Test/implementation order within a pair looked inverted.** The list keeps each
module next to its tests, which puts T002 before T003 and so on. A note in
Tasks' footer states that the test task runs first in every pair — the ordering
the repository's test-first discipline already requires — so the document does
not read as though implementation precedes its test.

Nothing else: no duplication, no ambiguity beyond measured quantities, no
terminology drift ("offered set", `TimeframeOption`, in-force token are used the
same way in all three artifacts), no constitution conflict, and every FR and SC
maps to at least one task.

## Metrics after resolution

- Requirements: 13 FR + 5 SC = 18; coverage 18/18 (100%).
- Tasks: 36 (34 implementation/test + 2 no-change guards), 14 marked `[P]`.
- Critical: 0. High: 0. Medium: 1 (resolved). Low: 3 (resolved).
- Ambiguity: 0. Duplication: 0. Unmapped tasks: none (Setup and Polish are
  cross-cutting by design).

## What is still open

- **Presentation remains open by design** — the requirement's Reference section
  postpones styling and component library; no task settles them.
- **The web gates are CI-only** (ADR-021). T035 runs them locally, but a
  contributor without the Node toolchain will learn about a TypeScript failure
  from CI rather than from the pre-commit hook. Unchanged by this feature and
  recorded here so it is not mistaken for one.
