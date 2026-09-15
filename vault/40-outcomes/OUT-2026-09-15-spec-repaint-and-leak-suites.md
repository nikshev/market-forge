---
id: OUT-2026-09-15-spec-repaint-and-leak-suites
step: spec
records: [REQ-NRT-REPAINT, REQ-NRT-LEAK]
commit: null
---

## What was done

Specified [[REQ-NRT-REPAINT]] and [[REQ-NRT-LEAK]] together as
`specs/114-repaint-and-leak-suites/spec.md`. One spec, because §35.4's closing
line — "This should be an automated CI suite" — is the requirement both share.

## What was decided

**Stored snapshots are compared against deep copies taken at production time.**
The existing test refits the same moment and compares, which proves the fit is a
function of its prefix and cannot see a model that hands out a correct value and
then mutates it. A shallow copy would not see it either, when the mutation is
inside a nested value — so the copy is deep, and that is written into the
requirement rather than left to whoever writes the test.

**Equality is by value, never by identity.** A model returning the same object
every call satisfies "all snapshots are equal" trivially under identity. This is
the kind of pass that looks like the strongest possible result.

**Each suite asserts its own coverage count.** An enumeration that reaches
nothing finds no violations and reports success — the same hazard that made
[[REQ-WP-072]]'s route gate assert 17 routes, and the same one that made
[[REQ-WP-071]]'s fixture-count assertion load-bearing. Third time this shape has
appeared; it is now something to write first rather than to discover.

**A feature that cannot be checked is refused, not skipped.** A skip reports
green, and a green suite is exactly what a leak needs in order to survive. The
refusal carries a reason the enumeration reads, so an unverifiable feature is
visible in the output rather than absent from it.

**"Every feature" means every registered specification, across all its exposed
columns.** 27 specifications expose 55 names; a leak in one column is a leak.

**The tolerance is relative and stated once.** Absolute tolerance is meaningless
across features whose units run from a ratio to a notional — and a tolerance
chosen after seeing which cases fail is the failure, renamed.

## What is still open

- **`planned` will be skipped.** Both requirements are `hard_gated`, and R5
  forbids a status past `specified` without a linked test. Per `/sdd-plan` step
  4, the next step writes the failing tests and records `tested` directly.
- **Whether §35.5 (live/replay parity) deserves the same treatment.** It is the
  third section in this family with no requirement note, and [[REQ-NRT-E]]
  covers replay parity for extrema only. Not in scope here; named so it is not
  discovered later as a surprise.
