---
id: SPEC-047-order-flow-exhaustion
requirement: REQ-EXP-014
speckit_path: specs/047-order-flow-exhaustion/spec.md
status: draft
---

## Summary

EXP-014 asks what the book does around a top, and then asks the question that
matters: whether any of it was available in time. Both studies run here over the
same seven series, and they are separate computations rather than one with a
flag — the arms differ in their window, in what they may read, and in what their
number means, and a shared path with a `retrospective` switch would be the
confusion the requirement names, one level down.

The conditional arm straddles each labelled turn and declares itself
retrospective in a field rather than a docstring: the thing a reader has to
carry away from that number is that it is not a forecast. PRD §13A.6 permits
exactly this use.

The predictive arm reads nothing at or after the bar it decides — including its
calling threshold, which is the half nobody looks at. A study can take only
trailing windows and still choose what counts as an extreme value from the whole
series, and the precision that results looks exactly like skill. `trailing_calls`
is public so that property is testable: the calls made over a prefix are the
calls the whole series makes at those same bars.

The finding EXP-014 exists to produce has a name in the report. A signal that is
extreme around every turn and flat at every decision reads as "explains the turn
but does not forecast it", and the report lists them.

## Links

- Requirement: [[REQ-EXP-014]]
- Builds on: [[REQ-WP-019]], [[REQ-EXP-004]]
