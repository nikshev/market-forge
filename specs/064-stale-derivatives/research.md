# Phase 0 — Research

## 1. Is the criterion actually unmet?

**Decision**: yes, and it is checkable rather than an opinion.

`state_at` returned the newest state at or before the instant with no upper
bound on its age. `crossvenue` excludes a quote past its tolerance and names
why; `book` and `alerting` guard it; §43's ranker penalizes it. `derivatives` —
the package the criterion names — had nothing.

## 2. Where does the rule go?

**Decision**: a free function, called from every reader of polled state.

**Rationale**: the plan's original answer was "the shared seam", and there isn't
one. `state_at` has no callers outside its own module. Placing the rule there
alone would have satisfied a reading of the requirement and protected nothing.

## 3. What about existing tests?

**Decision**: they pass an explicit `NOT_ABOUT_FRESHNESS`.

**Rationale**: fifteen failed on the new default, and every one of them was
about something else — a point-in-time join, a settled interval, a z-score
window. Passing an explicit wide tolerance says so out loud, which is better
than the previous state where a test passed because its fixture happened to sit
inside a window it never meant to be inside.

## 4. What if nothing has settled yet?

**Decision**: no value, not a stale value.

**Rationale**: a venue that has published states but settled no funding interval
has nothing to be stale about. Refusing there would report a freshness problem
where the honest answer is that there is no rate yet.
