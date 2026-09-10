# Phase 0 — Research

## 1. Exact horizons or buckets?

**Decision**: exact.

**Rationale**: labels are built with a stated `H`, so rows share exact horizons.
Bands would add a second arbitrary choice on top of `minimum_observations`, and
two arbitrary choices interact — a finding could then appear or vanish depending
on where a band edge fell, which is the kind of result nobody can argue with.

**What it costs**: a labeller that varied `H` per row would produce one slice per
row and a report that says nothing. Nothing does that today, and the failure
would be visible rather than silent.

## 2. What makes a slice unmeasurable?

**Decision**: too few rows, never too few positive outcomes.

**Rationale**: a target that never occurs at some horizon has observations and no
positives. That is a real calibration and usually a bad one — exactly the finding
worth surfacing. An implementation keying on positives would call it unmeasured
and hide it, which is the failure mode this whole requirement is about, one level
down.

## 3. Where the row shape comes from

**Decision**: a Protocol in `metrics.py`, not an import of `dataset`.

**Rationale**: `dataset.leakage` already establishes the pattern with `RowLike`.
Importing the dataset package into metrics would run the dependency backwards for
the sake of two fields.
