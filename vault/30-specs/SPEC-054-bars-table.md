---
id: SPEC-054-bars-table
requirement: REQ-TBL-001
speckit_path: specs/054-bars-table/spec.md
status: draft
---

## Summary

PRD §29.4's `bars`, and the first of §29.B's seventeen canonical tables to hold
real domain data. [[REQ-STORE-001]] built the plane; nothing wrote to it.

It lives in a third package because neither side may import the other: the
lakehouse must not learn what a `Bar` is, and the bar builder must not import a
storage backend. PRD §29.0 asks for exactly that — "backend-specific DDL must
live behind migrations/adapters and must not leak into signal/channel domain
code" — and both halves are already enforced by tests.

Two choices carry the design. Money is stored as its exact text, because float64
cannot hold a tenth and an Arrow decimal would need a precision per column that
§29's schemas do not give. And the event-time column is the bar's **close**, not
its open: a bar becomes knowable when it closes, and a point-in-time read
filtered on the open would hand over a window whose high, low and close had not
happened yet.

The writer is the bar builder's own `on_final` hook, so a replay fills the table
by the same path a live feed would.

## Links

- Requirement: [[REQ-TBL-001]]
- Builds on: [[REQ-STORE-001]], [[REQ-WP-005]], [[ADR-005]]
