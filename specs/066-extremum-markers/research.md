# Phase 0 — Research

## 1. Which instant is the event time?

**Decision**: `known_at_ns` for a confirmation, `observed_at_ns` for a
candidate.

**Rationale**: the plane's point-in-time read returns rows whose event time is
at or before the instant asked about. Keying on the turn's own instant would
make every such read a repaint — the chart would receive turns the system had
not yet confirmed, and no care downstream could recover it. Keying on knowledge
makes PRD §45's Phase 1A acceptance a property of the storage.

**What it costs**: the turn's instant is then an ordinary column, and a reader
sorting by event time gets confirmation order rather than turn order. `read_*`
sorts by the turn, because that is what a chart draws.

## 2. Optional measurements on a plane with no null

**Decision**: strings, empty for absent.

**Rationale**: a prominence of zero is a real reading. A float column would need
a sentinel, and every sentinel makes an unmeasured turn and a flat one the same
row. This is the fifth place in the repository the distinction has had to be
drawn.

## 3. Two lists or one with a flag?

**Decision**: two.

**Rationale**: a candidate and a confirmation are different claims. A caller
that had to tell them apart by inspecting a field is a caller that will
eventually forget, and the failure is silent — a candidate drawn as a
confirmation looks exactly like a confirmation.

## 4. Which mode filters?

**Decision**: `AS-SEEN-THEN` only.

**Rationale**: PRD §27.5 makes `CURRENT REFIT` the place where repaint-like
differences are meant to be visible. Filtering there would hide the very
difference the mode exists to expose, and it would do so while looking like
extra safety.
