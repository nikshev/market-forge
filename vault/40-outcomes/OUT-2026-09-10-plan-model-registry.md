---
id: OUT-2026-09-10-plan-model-registry
step: plan
records: [REQ-WP-022]
commit: null
---

## What was done

`specs/061-model-registry/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/registry.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-022]] moves to `planned`.

## What was decided

- **The hash covers hyperparameters as well as fitted state.** A model is what
  it learned and how it was told to learn.
- **Exact bytes.** `struct.pack` for floats, `tobytes()` plus dtype and shape for
  arrays. A platform producing different bytes has produced a different artifact.
- **The protocol gains `fitted`.** Three implementations signal it three ways and
  no outside test covers all of them. Two stand-ins that carry predictions rather
  than learning them answer `False`.
- **The registry lives with the models**, not in `experiments/`: an artifact hash
  is a property of a model, and the experiment registry is its consumer.
- **The three mappings are JSON strings in the table.** Their keys are the
  caller's, and a feature set nobody has invented yet must not require a schema
  change — which would change the fingerprint of every dataset citing the table.

## What is still open

- **Whether the length framing is load-bearing was not obvious**, and the answer
  changed a test. See the implement note.
