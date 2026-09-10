# Phase 0 — Research

## 1. What does "old stop" mean?

**Decision**: the stop that was in force when the move was decided.

**Rationale**: [[REQ-WP-033]] separated the decided stop from the active one, so
the phrase now has two possible referents. The decided one produces a message
announcing a move from a level the exchange never obeyed — a change that did not
happen, in a notification whose only job is to say what changed. It is carried
as its own field rather than derived, because deriving it would mean the
notification re-deciding what was active, and that is the replay's answer to
give.

## 2. One dispatcher or two?

**Decision**: one, made kind-agnostic.

**Rationale**: PRD §26.4 specifies retry, dead-lettering, audit and
never-block once. A second dispatcher would copy all four, and the copy would
diverge — the failure being one alert kind quietly not retried, visible only in
an audit nobody reads until something has already been missed.

**Cost**: `models.py` gains a deferred import of `render.py`. That is a real
layering compromise and is preferred to the two alternatives: moving §26.1's
renderer into the frozen record (a formatter inside a data model), or the second
dispatcher above.

## 3. What is announced?

**Decision**: a move, always. A hold or a refusal, only under debug, and never
in the shape of an update.

**Rationale**: §44A.34's "do not notify for rejected micro-updates unless debug
mode is enabled" admits two readings. The stricter one is safe in the direction
that matters: stop policies hold far more often than they move, and a channel
reporting every held micro-adjustment trains its reader to ignore it — losing
the alerts that matter exactly as silence would, but expensively.

Under debug the header differs, because "STOP UPDATED" above a stop that did not
move is a false sentence in the one mode a reader turns on because they distrust
what is happening.

## 4. Where does the identity come from?

**Decision**: derived from the position and the decision instant, per
[[ADR-017]].

**Rationale**: the same argument the signal id already carries. A generated id
makes a replay produce different notifications, different dedupe decisions and a
different audit, every one of them looking correct.

## 5. What does the suppression leave behind?

**Decision**: an audit record, always.

**Rationale**: `AlertGate` already established it — a suppression that leaves no
trace is indistinguishable from there having been nothing to say, and the
difference is what somebody is asking about when they ask why they heard nothing
all morning.
