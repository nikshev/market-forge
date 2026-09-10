---
id: OUT-2026-09-10-implement-experiment-gate-adoption
step: implement
records: [REQ-BIAS-011]
commit: null
---

## What was done

All eighteen research modules declare `EXPERIMENT` and `COMPARISON`, and every
comparison can be asked what it compared. `tests/unit/research/test_gate_adoption.py`
walks the package with `pkgutil` and fails on a module that lacks either, so the
list is discovered rather than maintained.

1482 fast tests green, mypy clean at 162 files. Mutation sweep over the seam: 19
mutants, 19 caught.

## What the work found

Four things that reading could not have told me.

- **An enum field collided into one config.** EXP-009's three corridor methods
  are enum members, which keep their identity in `_value_` — filtered out by the
  underscore rule — so all three hashed alike. The same failure the "hash the
  variant's name" design would have caused, arriving from the other side, and
  found by printing the configs rather than by reasoning.
- **A closure made a report non-deterministic.** EXP-012's turning methods carry
  a `slopes` closure built fresh per call, so keeping the function object gave
  two identical runs two different configs. `hashing.py` had already written
  down this failure's shape for `repr` — "a config hash different on every run
  for a reason nobody would find". It arrived through a dataclass field instead.
  Found by `test_two_runs_produce_equal_reports` going red, which is EXP-012's
  own determinism test doing exactly its job.
- **`config_of` was too strict and narrowed a working API.** `ChannelModel` is a
  Protocol, and EXP-001 has a test that passes a plain-class stub. Refusing
  non-dataclasses would have broken working code to serve a bookkeeping rule, so
  it now reports whatever the object exposes and says in its docstring how good
  that is.
- **EXP-010 was the module actually doing what rule 11 forbids.** It sweeps five
  thresholds, keeps the best in sample, and recorded only the winner — the four
  that lost left no trace anywhere. A reader could not tell a threshold that beat
  four rivals from one that was the only one to resolve a trade at all. Its field
  is now kept on every one of its four return paths, including the ones that
  chose nothing.

## What was decided

- **A comparison that chose nothing is not made to choose.** Seven of the
  eighteen report a field and no winner, and each says why in its own
  `compared` docstring against its own report's words: EXP-011 ranks nothing
  because its five metrics pull against each other, EXP-005 answers whether a
  difference is material rather than picking an arm, EXP-016 names no weighting
  between two readings that can disagree.
- **Being least bad is not being chosen.** EXP-013 and EXP-017 both have an arm
  that scores highest on a run their own gate refused. `chosen` is empty there;
  recording it as kept would report a promotion that did not happen.
- **EXP-013's promotion rule now returns the arm it picked.** The alternative
  was recomputing the tie-break in `compared`, which is a second copy of a rule
  that could disagree with the reason line printed beside it.
- **A variant's config carries the run's shared settings too.** Two runs of one
  model under different settings are two different runs, and an identity that
  ignored the settings would merge them.

## What is still open

- **The end-to-end path is proven for two experiments, not eighteen.**
  EXP-001 goes through the seam to the registry in a test, and EXP-010's field
  is asserted on two paths. The other sixteen are checked structurally — the
  property exists and returns a `Field`. A comparison whose `configs` were never
  populated would raise on `Field`'s empty-variants guard rather than record
  nothing, so the failure is loud; it is still a failure nothing catches until
  someone reports that experiment.
- **`config_of` sees only what an object exposes.** Two closures from one
  factory share a qualified name; an object holding its configuration on its
  class rather than its instance reports its type alone. Both are documented and
  tested as limits, and neither is currently reachable by a real variant.
- **Nothing forces a *reported* result through the seam.** The check reaches
  every module's comparison; it cannot reach a person who reads a report object
  and quotes one variant in a document. That is rule 11's honest limit, already
  stated in [[ADR-054]], and this work does not close it.
- **No caller assembles a run identity yet.** Dataset, code version and model
  artifact are the caller's, and nothing in the repository puts the three
  together for a research run. The seam is reachable; nothing reaches it in
  production code.
