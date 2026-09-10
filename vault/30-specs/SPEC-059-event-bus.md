---
id: SPEC-059-event-bus
requirement: REQ-INFRA-003
speckit_path: specs/059-event-bus/spec.md
status: draft
---

## Summary

PRD §45's Phase 0 lists "event bus abstraction" and says nothing more about it
anywhere. None of the phase's three acceptance criteria depends on it, so the
specification is written from the cost the current wiring actually has rather
than from an elaboration that does not exist.

That cost is specific: `BarBuilder(on_final=…)` and
`BacktestRunner(on_snapshot=…, on_candidate=…)` require a producer to be told
its consumer at construction, so **a producer cannot be observed by anyone it
was not built with**. A second consumer means changing the producer's
construction site.

Dispatch is synchronous and in subscription order, and that is written into the
requirement rather than left to the implementation: Principle XI depends on a
replay reproducing a result exactly, and a bus that reordered would break it at
the foundation while looking like plumbing.

The scope is the wiring that exists — [[REQ-PIPE-001]]'s replay path publishes
and its recorders subscribe. A publish/subscribe framework with no subscriber is
speculative generality, and Principle XIII says to build against the PRD's
phases and not ahead of them.

One line of the spec is there to stop a conclusion being chosen after the fact:
**if the replay path does not read better through the bus, that is a finding.**
The deliverable would then be closed by an argument rather than by code, and
[[REQ-PHASE-0]] would stay open.

## Links

- Requirement: [[REQ-INFRA-003]]
- The phase this unblocks: [[REQ-PHASE-0]]
- The wiring it replaces: [[REQ-PIPE-001]], [[REQ-WP-005]], [[REQ-WP-010]]
