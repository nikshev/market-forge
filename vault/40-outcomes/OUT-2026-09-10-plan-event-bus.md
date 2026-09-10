---
id: OUT-2026-09-10-plan-event-bus
step: plan
records: [REQ-INFRA-003]
commit: null
---

## What was done

`specs/059-event-bus/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/bus.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-INFRA-003]] moves to `planned`.

## What was decided

- **Producers receive a publishing hook; consumers subscribe.** The alternative
  — publish *alongside* the existing hooks — satisfies the deliverable's wording
  and leaves the cost exactly where it is. Producer signatures do not change:
  `on_final`, `on_snapshot` and `on_candidate` stay as they are and what changes
  is what gets passed to them, so `BarBuilder` and `BacktestRunner` stay ignorant
  of the bus and a caller can keep using them without one.
- **Exact-type dispatch.** A dict lookup rather than an MRO walk, and it avoids
  answering "does a subscriber to a base class see subclasses?" — a real
  question nobody here is asking.
- **`publish` iterates a copy.** The obvious implementation iterates the live
  list, and a handler that subscribes another one then gets either a
  `RuntimeError` or a silently skipped handler depending on which way the list
  mutated. Neither is a behaviour anyone would choose; both are what you get by
  not choosing.
- **A handler's exception propagates.** Catching so one bad handler cannot stop
  the rest buries the failure at the layer with least context about it.
- **No unsubscribe, buffer, retry or persistence.** Each is a real feature with
  no caller, and [[ADR-002]]'s plane is where durability lives.

## What is still open

- **Whether the abstraction earns its place is still not settled**, and the spec
  pre-committed to calling it a finding either way. The implement step is where
  that gets answered against the code rather than against the plan.
