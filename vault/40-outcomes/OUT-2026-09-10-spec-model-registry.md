---
id: OUT-2026-09-10-spec-model-registry
step: spec
records: [REQ-WP-022]
commit: null
---

## What was done

`specs/061-model-registry/spec.md`: three user stories, 11 functional
requirements, 8 success criteria. [[REQ-WP-022]] moves to `specified`.

## What was decided

- **The hash covers the fitted parameters *and* the hyperparameters.** Two
  models that landed on identical weights from different penalties are not one
  artifact — one will behave differently on the next dataset, and a hash merging
  them would certify a reproduction that is not one.
- **Exact bytes, not rounded.** Two fits differing in the last bit produce
  different probabilities. A hash that rounded them together would lie about the
  one thing it exists to certify, and a platform producing different bytes has
  produced a different artifact.
- **The model says whether it is fitted.** Only it knows: `ElasticNetLogistic`
  holds `_weights = None`, a GMDH network holds empty layers, and there is no
  outside test that covers both. The protocol gains one member, the way
  `Transform.centered` did, so an author of the next model cannot skip the
  question.
- **A stored hash is read, never recomputed.** A hash recomputed from a
  registration is a hash of the registration: it would pass every round-trip
  test while certifying nothing about the model.
- **An unresolvable hash is refused.** Accepting one would let a run look
  reproducible by naming a string — the same distinction [[REQ-REPRO-001]] drew
  between `NO_MODEL` and `UNRECORDED`, one level further out.

## What is still open

- **Adding a member to the `Model` protocol touches four models**, and whether
  each can answer honestly is not settled until it is written. A model whose
  fitted state is indistinguishable from its unfitted state would have to change
  more than a property.
- **Cross-platform reproducibility is deliberately not claimed.** A result
  reproduced on different hardware may hash differently, and the spec calls that
  honest rather than solving it. Whether that is the right trade for this project
  is a question the PRD does not answer.
