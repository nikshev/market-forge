---
id: OUT-2026-09-10-requirement-event-bus
step: requirement
records: [REQ-INFRA-003]
commit: null
---

## What was done

[[REQ-INFRA-003]] extracted by hand from PRD §45's Phase 0 deliverable list. It
is the last of Phase 0's nine deliverables with nothing behind it, and the only
entry in [[REQ-PHASE-0]]'s `not_delivered`.

## What was decided

- **The acceptance is derived, not quoted.** The PRD says "event bus
  abstraction;" and nothing else — no section elaborates it, and none of Phase
  0's three acceptance criteria depends on it. The extractor would have written
  `ACCEPTANCE-NOT-SPECIFIED`, so the criteria come instead from what the three
  existing producers already do and from Principle XI.
- **The scope is the wiring that exists.** `BarBuilder.on_final`,
  `BacktestRunner.on_snapshot` and `on_candidate` each require a producer to be
  told its consumer at construction. The bus removes that, and the replay path
  is what will use it. A publish/subscribe framework with no subscriber is
  speculative generality, and Principle XIII says to build against the PRD's
  phases and not ahead of them.
- **Synchronous and ordered is part of the requirement, not of the design.** A
  bus that dispatched concurrently or reordered would break Principle XI at its
  foundation while looking like an implementation detail, so it is written into
  the acceptance where a reviewer will see it.

## What is still open

- **Whether the abstraction earns its place is not settled by writing this
  note.** The honest test is whether the replay path reads better through the bus
  than through direct hooks. If it does not, that is a finding to record rather
  than a conclusion to avoid — the deliverable would then be closed by an
  argument instead of by code, and [[REQ-PHASE-0]] would stay open.
- **Live mode remains out of scope.** PRD §25.1's other mode is what a bus most
  obviously serves, and it does not exist. This requirement does not build it.
