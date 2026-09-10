---
id: OUT-2026-09-10-spec-event-bus
step: spec
records: [REQ-INFRA-003]
commit: null
---

## What was done

`specs/059-event-bus/spec.md`: three user stories, 10 functional requirements,
8 success criteria. [[REQ-INFRA-003]] moves to `specified`.

## What was decided

- **The spec is written from a measured cost, not from the PRD line.** "Event
  bus abstraction;" has no elaboration and no acceptance behind it, which means a
  specification could say almost anything and still look faithful. The one
  concrete problem the bus solves today is checkable in the source: `BarBuilder`
  and `BacktestRunner` require their consumers at construction, so a producer
  cannot be observed by anyone it was not built with.
- **Synchronous, ordered dispatch is in the requirement.** Principle XI depends
  on it. Left to the implementation, it is the kind of property that gets
  changed for throughput by someone who does not know a replay depends on it.
- **A subscriber's exception propagates.** The alternative — catching and
  continuing so one bad handler cannot stop the rest — sounds robust and hides
  the failure at exactly the layer that has least context about it.
- **Exact-type dispatch, not inheritance.** A real feature nobody needs; adding
  it later is easier than removing it.
- **The conclusion was pre-committed.** "If the replay path does not read better
  through the bus, that is a finding" is in the spec's assumptions, written
  before the work. A deliverable nobody asked to use is exactly where the
  temptation to declare success afterwards lives.

## What is still open

- **Whether the abstraction earns its place is genuinely unsettled.** The replay
  path is the only consumer today, and it already works. If routing it through a
  bus makes it longer without making anything possible, the honest outcome is to
  say so and leave [[REQ-PHASE-0]] open rather than close a deliverable with
  ceremony.
- **Live mode is what a bus most obviously serves and does not exist.** PRD
  §25.1's other mode would give the abstraction a second consumer and a real
  reason; this work does not build it.
