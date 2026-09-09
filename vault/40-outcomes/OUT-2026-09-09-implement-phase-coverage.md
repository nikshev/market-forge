---
id: OUT-2026-09-09-implement-phase-coverage
step: implement
records: [REQ-PHASE-0, REQ-PHASE-1, REQ-PHASE-1A, REQ-PHASE-2, REQ-PHASE-3, REQ-PHASE-4, REQ-PHASE-5, REQ-PHASE-6, REQ-PHASE-7, REQ-PHASE-7A, REQ-PHASE-8]
commit: null
---

## What was done

All eleven `REQ-PHASE-*` notes moved from `draft` to `planned`, each carrying
a `covers:` list, a `not_delivered:` list and a `## Coverage` section.
`tests/tools/trace/test_phase_coverage.py` checks both lists: 13 tests.

## The survey is the result

The gap lists came from reading the deliverables against the repository, and the
answer was the same for every phase: something is missing. That is why all
eleven are `planned` and none is `implemented`.

- **Phase 0** has no virtual clock, no event bus abstraction and no ClickHouse
  connectivity, though the rest of the skeleton is there and green.
- **Phase 1A** has the whole extremum lifecycle and no chart markers for
  candidate versus confirmed extrema.
- **Phase 2** has every book and flow feature and no UI pane showing them.
- **Phase 4** has the EVM connector and the Uniswap v3 adapter, and none of
  Aerodrome, Curve, Uniswap v4, HyperCore, Pinot or Iceberg.
- **Phase 5** has the cross-venue engine and only one venue connector.
- **Phase 6** has the point-in-time dataset, the walk-forward runner and the
  ablations, and no experiment registry and no dataset hashes.
- **Phase 7** has every model and no model registry.
- **Phase 7A** has the stop engine and its counterfactual replay, and no
  stop-path chart and no stop-update notification.
- **Phase 8** has nothing.

The easy version of this work sets eleven statuses to `implemented` and writes
nothing down. Each of those eleven would have been contradicted by its own note.

## What was decided

- **A phase is its deliverables.** A phase with one missing deliverable is a
  phase in progress, however much of it is built.
- **The gap lines are specific.** "UI panes for the book features: the web app
  has no order-book or order-flow pane" can be disagreed with; "UI incomplete"
  cannot.
- **The marker scan stays.** Ten notes have left the list and the extractor can
  still put a note back on it.

## What is still open

- **Every phase's gap list is work nobody has scheduled.** Listing it is not
  planning it, and the largest of them — Phase 4's five missing protocol
  adapters and Phase 8 entirely — are each larger than most work packages here.
- **No phase has been promoted.** The machinery allows `implemented` when a gap
  list empties; nothing in this change empties one.
- **The coverage lists are hand-written.** A requirement that delivers part of a
  phase and is not listed is invisible to the test, which checks the claims made
  rather than discovering the ones that were not.
