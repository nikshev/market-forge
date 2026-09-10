# Phase 0 — Research

## 1. Do producers publish, or does the wiring publish for them?

**Decision**: producers receive a publishing hook; consumers subscribe.

**Rationale**: the cost this feature exists to remove is that a producer cannot
be observed by anyone it was not constructed with. Publishing *alongside* the
existing hooks would leave that cost untouched and satisfy the deliverable's
wording anyway, which is the failure mode the spec's last assumption was written
to catch.

Producer signatures do not change: `on_final`, `on_snapshot` and `on_candidate`
stay exactly as they are, and what changes is what gets passed to them. That
keeps `BarBuilder` and `BacktestRunner` ignorant of the bus, which is the
property that lets a caller keep using them without one.

**Alternatives considered**:
- *Give the producers a `bus` parameter.* Couples every producer to the bus and
  makes the plain hooks a second path, which Principle VII spent effort removing.

## 2. Exact type, or inheritance?

**Decision**: exact type.

**Rationale**: a `dict[type, list[handler]]` lookup is O(1) and obvious.
Inheritance-based dispatch means walking the MRO on every publish and answering
"does a subscriber to a base class see subclasses?" — a real question nobody
here is asking. Adding it later is easy; removing it once someone depends on it
is not.

## 3. What happens to a subscription made during dispatch?

**Decision**: it does not receive the event in flight. `publish` iterates a copy.

**Rationale**: the obvious implementation iterates the live list, and mutating a
list while iterating it is either a `RuntimeError` or a silently skipped
handler, depending on which way it is mutated. Neither is a behaviour anyone
would choose; both are what you get by not choosing.

## 4. A subscriber raises — catch or propagate?

**Decision**: propagate.

**Rationale**: catching so one bad handler cannot stop the rest sounds robust and
buries the failure at the layer with least context about it. In a replay a
swallowed handler is a missing row nobody hears about; the whole point of the
canonical plane is that what is recorded is what happened.
