# Phase 0 — Research

## 1. Where does detection happen?

**Decision**: a second pass over the same bars, inside `record_replay`.

**Rationale**: the backtest runner owns its loop and offers no per-bar hook.
Adding one so a detector could ride along would change a component that has
nothing to do with extrema, to save an iteration over a list already in memory.
Principle VII is about the *events* being identical to a live process's, not
about the iteration being shared.

## 2. Per bar, or a batch at the end?

**Decision**: per bar.

**Rationale**: a batch produces the same rows and a different event stream, and
the difference is invisible until a live process attaches the same subscribers
and sees a burst. The test counts alternations rather than asking whether the
sequence is sorted — the sorted check passes for the batch version too, which
the mutation sweep found.

## 3. Which instant does the watermark read?

**Decision**: `known_at_ns` and `observed_at_ns` — knowledge, not the turn.

**Rationale**: those are what the tables are keyed by ([[REQ-WP-028]]), so the
watermark and the storage agree by construction. Reading the turn's own instant
would skip a confirmation that arrived late about an early turn — silently, and
only on a re-run.

## 4. The detector accumulates rather than calling back

Candidates land on a list inside it, so publishing them per bar means noticing
what was appended by its count. That reads a little awkwardly and is the honest
shape: changing the detector to emit them is [[REQ-WP-019]]'s decision, and this
requirement is a caller, not a redesign.
