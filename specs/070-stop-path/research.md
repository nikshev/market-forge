# Phase 0 — Research

## 1. How is "do not recompute" made checkable?

**Decision**: the module is never given bars.

**Rationale**: "must not recompute a prettier trail" is a statement about
intent. No test can assert intent, and a reviewer catches it only by noticing an
argument that should not be there. Removing the input inverts that: a function
with no price series cannot produce a price-derived trail, and the next person
who wants one has to add a parameter, which is visible in a diff.

**Alternatives considered**: a test comparing against a golden path. It would
pass for an implementation that recomputes correctly *today* and would go on
passing when the anchor logic changed underneath it.

## 2. What proves the path is carried rather than derived?

**Decision**: draw the same position against two different futures and require
the same path.

**Rationale**: it is the one assertion no recomputing implementation can pass,
and it does not depend on knowing what the right trail looks like. Every weaker
form — a fixed expected path, a spot check on one point — is satisfied by a
recomputation that happens to agree on that input.

## 3. What happens to an anchor the proposal could not have known?

**Decision**: refuse the whole view, naming the proposal.

**Rationale**: this is the corrupted case, not the absent one. A proposal
carrying an anchor confirmed after the proposal was made is the look-ahead the
requirement exists to prevent, arriving as data. Dropping the anchor quietly
would render a clean-looking chart from a path that is wrong; drawing it would
render the forbidden chart. Neither leaves the reader anywhere to notice.

The states follow `panes.ts`: a rendering answer carries `ok`, `empty` or a
refusal with a note, rather than throwing into a render ([[REQ-WP-009]]'s rule
that a failed load is never drawn as data).

## 4. Is a hold a point on the path?

**Decision**: yes, and it keeps its reasons.

**Rationale**: [[ADR-032]] refused to let a hold be `None` so that six kinds of
hold stay distinguishable in the model. Drawing only movements undoes that at
the last step. A stop held on a cooldown and one held because nothing was
knowable are the same flat line and different facts, and the second is a gap in
knowledge the reader should see.

**Alternatives considered**: a hold as a tooltip on the surrounding movement.
Rejected — a run of holds with no movement around it would have nowhere to live.

## 5. Which figures does the view compute?

**Decision**: risk from the position; excursion from the recorded outcome.

**Rationale**: open risk is entry against current stop over accepted initial
risk — three numbers the position carries. MFE and MAE are of an observed path,
and the replay is where the path and the side already meet, so recomputing them
in the view would re-derive the side convention in a second place. This is the
correction recorded in `plan.md`.
