# Phase 0 — Research

## 1. Where does the artifact hash come from?

**Decision**: `compare` reports it; the run does not refit.

**Rationale**: refitting to obtain a hash is a second scoring path, and a
comparison is only honest if one code path produced both numbers. The hash is
taken where the fitted model is in scope and is correct by construction.

**What it cost**: `BaseRate` could not answer `fitted`. An unfitted base rate is
0.5 and one fitted on a balanced target is also 0.5, so no test over its state
can tell them apart — it has to remember. That is the case [[REQ-WP-022]]'s
protocol member exists for, found by 58 tests going red.

## 2. One artifact per variant, or per fold?

**Decision**: per variant, over its folds in order, one contribution per fold.

**Rationale**: what a result cites is the variant *as run*. A variant appearing
twice in one fold — as the subject and as a baseline of the same name — was
fitted identically both times, so counting it twice would give it a longer
artifact than its rivals for no reason a reader could recover.

## 3. Who decides the winner?

**Decision**: lowest rows-weighted Brier, and only if it beat the base rate.

**Rationale**: a model that cannot beat a base rate is not a model — PRD §23.6's
own argument, and §45's Phase 7 acceptance turns on it. `None` otherwise, which
is a promotion that did not happen rather than a field with no best member.

## 4. Where do the shared fixtures live?

**Decision**: moved up to `tests/unit/conftest.py`.

**Rationale**: the study needs the same rows, folds and certificate the turning
tests use. Copying them would be two fixtures that drift, and a study asserting
against a copy of a dataset the turning tests no longer use is a test asserting
about its own fixture.
