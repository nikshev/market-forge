---
id: OUT-2026-09-10-spec-extremum-markers
step: spec
records: [REQ-WP-028]
commit: null
---

## What was done

`specs/066-extremum-markers/spec.md`: three user stories, 12 functional
requirements, 8 success criteria. [[REQ-WP-028]] moves to `specified`.

## What was decided

- **FR-005 and FR-007 are a pair.** One says when a confirmation may be returned,
  the other where it is drawn. Separately, an implementation could satisfy the
  PRD's criterion by drawing the turn at its `known_at` — never too early, and
  also not where the turn happened.
- **The same rule applies to candidates**, which the PRD's criterion does not
  mention. A candidate leaking in before it was observed is the same defect under
  a different name, and nothing in the document would have caught it.
- **Window and knowledge are separate filters.** Collapsing them makes a
  correctness rule look like a range query, and a later refactor that simplified
  one would take the other with it.
- **An unconfirmed candidate is still drawn.** The obvious implementation drops
  it as noise; a swing that did not confirm is a fact about the market, and
  hiding it makes the detector look better than it is.

## What is still open

- **How the two markers differ is not fixed.** Shape, colour or fill are all
  honest; being told apart is the requirement, and a reviewer may prefer another
  answer than the plan's.
- **Whether a candidate should disappear the moment its confirmation arrives, or
  fade**, is a question this spec answers only as "not drawn twice".
