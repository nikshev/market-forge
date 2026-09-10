---
id: REQ-INFRA-003
title: One event bus carries what the producers produce to whoever consumes it
type: infrastructure
prd_ref: "Phase 0 — Repository + correctness skeleton"
prd_lines: "6685-6685"
phase: 0
status: implemented
depends_on: [REQ-WP-005, REQ-WP-010, REQ-PIPE-001]
tags: [tooling]
---

## Requirement

PRD §45's Phase 0 deliverables list, one line:

    - event bus abstraction;

That is the whole of what the PRD says about it. No section elaborates it, and
none of Phase 0's three acceptance criteria — `make test` green, services boot
locally, canonical event serialization roundtrip — depends on it. It is the last
of Phase 0's nine deliverables with nothing behind it, and it is why
[[REQ-PHASE-0]] cannot leave `planned`.

So the requirement is written from what the system already needs rather than
from an elaboration that does not exist. Three producers emit events today and
each hands them to a consumer it was constructed with:

- `BarBuilder` calls `on_final` when a window closes;
- `BacktestRunner` calls `on_snapshot` for each fitted channel and `on_candidate`
  for each live signal;
- [[REQ-PIPE-001]]'s replay wires those three to recorders that write to the
  canonical plane.

A producer therefore has to be told, at construction, who will consume it. The
bus is the abstraction that removes that: a producer publishes, and whoever
wants the event subscribes.

**Synchronous and ordered, deliberately.** Principle XI requires a replay to
reproduce a result exactly, and a bus that dispatched concurrently or reordered
would break that at its foundation while looking like an implementation detail.

## Acceptance

- a producer publishes an event without naming its consumers;
- a consumer subscribes to an event type and receives every event of that type;
- an event with no subscriber is published without error and without effect;
- handlers run synchronously, in subscription order, so two identical runs
  deliver identical sequences;
- a handler that raises does not silently swallow the failure;
- the replay path publishes through the bus, so the abstraction has consumers
  rather than being available to none;
- what a replay records is unchanged: the same bars, snapshots, signals and
  dataset identity as before the bus existed.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-059-event-bus]]
- **Tests:**
    - `tests/unit/pipeline/test_replay.py::test_a_caller_can_observe_a_replay_without_editing_it`
    - `tests/unit/pipeline/test_replay.py::test_a_caller_can_observe_finalized_bars`
    - `tests/unit/pipeline/test_replay.py::test_an_observer_does_not_change_what_is_recorded`
    - `tests/unit/test_bus.py::test_a_subscriber_to_another_type_receives_nothing`
    - `tests/unit/test_bus.py::test_a_subscribers_exception_reaches_the_publisher`
    - `tests/unit/test_bus.py::test_a_subscription_made_during_dispatch_waits_for_the_next_event`
    - `tests/unit/test_bus.py::test_an_event_with_no_subscriber_is_published_without_effect`
    - `tests/unit/test_bus.py::test_dispatch_is_by_exact_type`
    - `tests/unit/test_bus.py::test_every_subscriber_to_a_type_receives_the_event`
    - `tests/unit/test_bus.py::test_subscribers_run_in_subscription_order`
    - `tests/unit/test_bus.py::test_the_same_handler_subscribed_twice_is_called_twice`
    - `tests/unit/test_bus.py::test_two_identical_runs_deliver_identical_sequences`
- **Code:**
    - `src/channelflow/bus.py`
    - `src/channelflow/events.py`
- **Outcomes:** [[OUT-2026-09-10-implement-event-bus]], [[OUT-2026-09-10-plan-event-bus]], [[OUT-2026-09-10-requirement-event-bus]], [[OUT-2026-09-10-spec-event-bus]]
<!-- trace:end -->

## Notes

Extracted by hand, not by `tools/extract_prd.py`: the PRD line is a deliverable
with no section behind it, and the extractor would have written
`ACCEPTANCE-NOT-SPECIFIED`. The acceptance above is **derived, not quoted** —
each line comes from what the three existing producers do and from Principle XI,
and the derivation is the body of this note.

The scope is deliberately the wiring that exists. A bus with no subscriber is
speculative generality, and Principle XIII says to build against the PRD's
phases and not ahead of them — so this closes the deliverable with something the
replay path actually uses, rather than a publish/subscribe framework waiting for
a caller.
