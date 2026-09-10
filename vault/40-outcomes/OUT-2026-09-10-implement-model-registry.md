---
id: OUT-2026-09-10-implement-model-registry
step: implement
records: [REQ-WP-022]
commit: null
---

## What was done

`models/registry.py`: `artifact_hash`, `Registration`, `ModelRegistry` on the
canonical plane, and `require_registered`. The `Model` protocol gained `fitted`,
implemented by four models and two stand-ins.

25 new tests, 1556 in the suite, mypy clean at 167 files, 11 of 11 mutants
caught.

**PRD §0 item 13's fourth hash now has a producer.** A run that fitted a model
can record its artifact hash instead of `UNRECORDED`, and a run citing a hash
nobody registered is refused rather than accepted as a string.

## What the mutation sweep found

Four of eleven mutants survived the first pass, and every one of them pointed at
a test that claimed more than it checked.

- **The hyperparameter test was not testing hyperparameters.** Two
  `ElasticNetLogistic`s with different penalties also *fit to different weights*,
  so a hash covering only the fitted state passed it. The isolated case copies
  the fitted state unchanged and moves one hyperparameter, which is then the only
  thing left to tell them apart.
- **Nothing exercised the "exact bytes" claim.** No two models in the tests
  differed below printing precision, so hashing a rounded `repr` passed
  everything. Now one does, by a nudge of `1e-16`.
- **Nothing exercised dtype and shape.** An array reshaped without changing a
  byte is a different model — it predicts differently, or not at all — and
  hashing only `tobytes()` called them one.
- **The collision test could not collide.** Two plain string fields cannot: the
  field names absorbed between them anchor every position, so the test passed
  with the framing removed. Searching for a real collision found one in a
  mapping, which has no anchors — `{"a": "sb"}` and `{"as": "b"}` produce
  byte-identical output unframed, because the tag that starts a value is
  indistinguishable from the last character of a key. A model holding
  per-feature scaler parameters is exactly that shape.

That last one is the more useful finding: the framing *is* load-bearing, and the
first test written to prove it proved nothing.

## What is still open

- **Nothing fits and registers a model in one path yet.** The pieces exist and
  the research modules construct models directly. Wiring an experiment to
  register what it fitted is a change to those modules and belongs with whoever
  next touches EXP-008 or EXP-013.
- **Cross-platform reproducibility is not claimed.** A result reproduced on
  different hardware may hash differently. The spec calls that honest; whether it
  is the right trade is a question PRD §0 item 13 does not answer.
- **[[REQ-PHASE-7]] keeps one deliverable open** — "P(max)/P(min)/P(no-turn)
  calibration by horizon" — so the phase stays `planned`.
