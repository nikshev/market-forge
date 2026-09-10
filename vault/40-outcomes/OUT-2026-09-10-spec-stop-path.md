---
id: OUT-2026-09-10-spec-stop-path
step: spec
records: [REQ-WP-032]
commit: null
---

## What was done

`specs/070-stop-path/spec.md`: three user stories, 10 functional requirements,
6 success criteria. [[REQ-WP-032]] moves to `specified`.

## What was decided

- **FR-001 is enforced by the signature.** The rule "do not recompute the trail"
  is a promise about intent and cannot be tested. "The module is never handed a
  price series" is a fact about a signature, and a view with no bars cannot
  recompute a trail from them. This is the one place the spec deliberately bends
  the no-implementation-details rule, because the checkable form of the rule is
  the only useful form of it.
- **SC-001 is the criterion that cannot be satisfied by accident**: draw the
  same position against two different futures and require the same path. Any
  implementation that touches price at all fails it.
- **A hold is not a gap.** Four functional requirements exist to stop the view
  collapsing [[ADR-032]]'s six distinguishable holds back into one flat line at
  the last step before a human reads it.
- **Unknown reason codes are carried through, not dropped.** A view that
  silently drops a reason it does not recognise turns a newly added veto into no
  veto at all, and it would look like nothing happened.
- **Two of §44A.33's fifteen fields have no producer** — trail aggressiveness
  and data-health status. Named in Open Questions rather than dropped: a spec
  that omitted them would read as complete while losing the two hardest fields.

## What is still open

- **Nothing stores stop proposals.** [[REQ-WP-020]] built the engine; no table
  holds its output and no endpoint serves it. This specifies the view over the
  shape the engine already produces, as [[REQ-WP-030]] specified panes over
  features nothing writes.
- **Trail aggressiveness** and **data-health status**, as above.
- **The "why not tighter" grouping** is this feature's; whether it belongs
  nearer the policy that produced the codes is a fair question and is not
  settled here.
