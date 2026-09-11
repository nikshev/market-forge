---
id: OUT-2026-09-11-implement-dataset-lineage
step: implement
records: [REQ-WP-040]
commit: null
---

## What was done

`DatasetOrigin`, `resolve` and `pins_for` in `models/registry.py`; the field on
`Registration`, persisted in three columns; `run_study` threads it. 19 tests,
8 of 8 mutants caught, every gate green.

[[REQ-WP-040]] reaches `implemented`, and PRD §0 item 13's fourth requirement
has a home for the first time.

## A design change made during implementation

The plan put the origin on `CertifiedDataset`, so a study would carry it through.
That was wrong, and building it showed why: `certify` is also called over rows a
fixture or a research script built in memory, which came from no table at all.
Requiring an origin there would have forced every synthetic dataset to **invent
one** — a plausible value where there is no fact, which is the failure this
codebase spends most of its tests on.

The origin is `run_study`'s argument instead. A run that registers a model must
cite real data; a dataset that was never in a table cannot be studied, and that
is the correct refusal rather than an inconvenience.

## What the sweep found

Six mutants died against the first test set. Two survived, and both were cases
nobody had written:

- **A citation with no hash was accepted.** A snapshot id is a name; without the
  hash there is nothing to check it against and the citation would pass forever.
- **Pins ignored which table they were for.** Every test used one table, so a
  filter that always said yes looked right. With two tables the mutant keeps one
  lineage alive and lets the other go — which is worse than no pinning, because
  it looks like pinning.

## A mistake worth recording

I overwrote `tests/unit/models/conftest.py` with a new file instead of appending
to it, deleting four fixtures another suite depended on. `git checkout` restored
it in seconds because the file was tracked and committed; had it been either of
those things less, the fixtures would have been gone.

The reason it happened is worth more than the fix: I assumed the conftest did
not exist because I had not looked. Writing a file is not additive, and "create
the fixture I need" and "add a fixture to the file that is there" are different
operations that look identical while typing.

## What is still open

- **Whether `require_registered` should refuse a stale citation.** Making it
  fatal would catch a wrong dataset at the point of use and also make every
  report unreadable after a legitimate retention pass.
- **One dataset per registration**, which is right while a run reads one table
  at one snapshot.
- **Nothing calls `pins_for` in production**, because nothing schedules a
  retention pass. The loop is closed in the code and not yet in the operation.
