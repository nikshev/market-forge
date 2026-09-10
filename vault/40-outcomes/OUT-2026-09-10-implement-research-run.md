---
id: OUT-2026-09-10-implement-research-run
step: implement
records: [REQ-WP-024]
commit: null
---

## What was done

`pipeline/study.py`'s `run_study`. **Five mechanisms that had no caller now have
one**: run identity, the field seam, the artifact hash and its registry, and
calibration per horizon.

1587 tests, mypy clean at 168 files, 13 of 14 mutants caught and the
fourteenth documented.

## The two findings

Both are changes to things this requirement was supposed to only *use*, and both
were pre-committed to being reported as findings.

- **`report_comparison` took one model artifact for a whole field.** A comparison
  that fits its variants gives each a different artifact, so a single value would
  have recorded four models under one hash — four runs that look like
  reproductions of each other. It now accepts a mapping.
  [[SPEC-057-experiment-gate-adoption]] said in as many words that if adoption
  needed the gate to change, that was a finding to record rather than absorb.
- **`BaseRate` could not say whether it had been fitted.** An unfitted base rate
  predicts 0.5 and one fitted on a balanced target also predicts 0.5, so no test
  over its state can tell them apart — it has to remember. Found by 58 tests
  going red at once, and it is the clearest vindication of [[REQ-WP-022]]'s
  decision to make `fitted` a protocol member rather than infer it.

## What the mutation sweep found

Four survivors on the first pass, three of them real:

- **A variant's artifact could have been one fold's.** Nothing compared the
  combined hash against a single fold's: registering, resolving and
  run-hash equality all pass either way. The test now recomputes the combination
  from the returned comparison — which is also why `StudyResult` returns the
  comparison at all.
- **`compare` dropping its subject's artifact was invisible**, because EXP-008's
  subject shares a name with one of its baselines and the baseline supplied one
  under the same name. The new test uses a distinct model so the subject answers
  for itself.
- **The per-variant mapping could have been ignored** and every identity read
  `NO_MODEL`; nothing checked the seam's own identities.

The fourth is deliberate. `require_registered` in the run is **unreachable by
construction** — the run registered every artifact it is about to cite a few
lines earlier — and is kept because it is what makes FR-008 true for the next
caller, which may register somewhere else or not at all. The docstring says a
mutation of it survives and should.

## What is still open

- **One experiment is wired.** Whether the path generalises is unknown by
  construction; a second caller that needs a different path is a finding about
  the path.
- **The registration's spans are placeholders.** `train_start_ns` and its three
  siblings are 1/2/2/3 because a fold's own boundaries are not carried on the
  `ComparisonReport` that reports it. PRD §23.9 asks for the real ones, and this
  records shape rather than truth for those four fields.
- **`require_causal` still has no live call site.** A research run is not a live
  feature path, so [[REQ-BIAS-002]]'s third gap is untouched.
