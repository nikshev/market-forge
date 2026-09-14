---
id: REQ-WP-069
title: A phase says what remains, what waits on somebody else, and what was decided against
type: work-package
prd_ref: "§45"
prd_lines: "6760-6920"
phase: null
status: implemented
depends_on: [REQ-PHASE-4, REQ-WP-068]
tags: []
---

## Requirement

Every phase note carries `covers:` and `not_delivered:`, and
`test_phase_coverage.py` makes both mean something: a phase at `implemented`
with a non-empty `not_delivered:` is "claiming to be finished while listing what
is missing".

That rule is right and stays. **The list it guards has stopped being one kind of
thing.** Phase 4's three entries are:

    Curve twocrypto quoting     the deployed version has no published source
    Pinot HOT DeFi datasets     [[ADR-002]] defers it until a HOT requirement exists
    Uniswap v4 quoting          nobody has built it

The first waits on Curve. The second is a decision this project made and
recorded. Only the third is work anybody here can do — and because all three sit
in one list, **Phase 4 cannot reach `implemented` however much of it is
finished**. The measure stops answering the question it is read for, which is
what is left to do.

### The danger is relabelling, not the three lists

Splitting a list is trivial. What makes it honest rather than a way to declare
victory is that the two new lists cost something to use:

- a `blocked:` entry names **what it waits on**, so "blocked" cannot mean "not
  started";
- a `deferred:` entry names **the decision**, as an ADR that exists, so
  deferring requires having decided rather than having skipped.

Without those, moving an entry left to right would close any phase at will. With
them, the move requires either an external cause that can be checked or a
recorded decision that can be read.

### What the lists are for

`not_delivered:` — work that remains and that this project can do. A phase at
`implemented` has none.

`blocked:` — a deliverable waiting on something outside this repository. It does
not stop a phase closing, because a phase cannot deliver what it is not allowed
to, and pretending otherwise makes every later phase look unfinished too.

`deferred:` — a deliverable this project decided against, for now or for good.
The ADR is the justification, and a reader who disagrees has something to
disagree with.

## Acceptance

- Every phase note carries all three lists, even empty ones — an absent list
  reads as "nothing there".
- A phase at `implemented` has an empty `not_delivered:`; `blocked:` and
  `deferred:` may hold entries.
- Every `blocked:` entry names what it waits on; an entry that does not is a
  failure, not a pass.
- Every `deferred:` entry names an ADR, and that ADR exists.
- Phase 4's three entries are sorted into the three lists, each keeping the
  wording that already explains it.
- The dashboard and any reader of these lists keep working, and a phase that
  closes on `not_delivered` alone still shows what it is waiting on.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-110-phase-accounting]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_a_blocked_entry_that_names_no_blocker_is_refused`
    - `tests/tools/trace/test_phase_coverage.py::test_a_blocked_entry_that_names_one_passes`
    - `tests/tools/trace/test_phase_coverage.py::test_a_deferred_entry_pointing_at_no_such_decision_is_refused`
    - `tests/tools/trace/test_phase_coverage.py::test_a_deferred_entry_with_a_real_decision_passes`
    - `tests/tools/trace/test_phase_coverage.py::test_a_deferred_entry_without_a_decision_is_refused`
    - `tests/tools/trace/test_phase_coverage.py::test_every_phase_carries_all_three_lists`
- **Code:**
    - `tools/trace/phases.py`
- **Outcomes:** [[OUT-2026-09-14-implement-phase-accounting]]
<!-- trace:end -->

## Notes

This changes a measure, not a behaviour. It is worth doing because the measure is
what every answer to "what is left" has been built on, and two of Phase 4's three
entries have been making that answer wrong in the same direction for weeks.
