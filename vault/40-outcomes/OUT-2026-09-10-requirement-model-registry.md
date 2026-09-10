---
id: OUT-2026-09-10-requirement-model-registry
step: requirement
records: [REQ-WP-022]
commit: null
---

## What was done

[[REQ-WP-022]] extracted from PRD §23.9, which gives eleven named fields. Unlike
the two deliverables closed before it today, this one is specified and nothing
had to be derived.

## What was decided

- **The requirement is written around the gap, not around the list.** Eleven
  fields are easy to store. What makes this worth building is that
  `ModelArtifact` appears nowhere outside `channelflow.experiments`, so every run
  that fitted a model records `UNRECORDED` — the value whose whole job is to say
  the run cannot be reproduced. This is the fourth of PRD §0 item 13's four
  hashes and the last with no producer.
- **The artifact hash is over the fitted parameters**, not over the
  registration. §23.9 lists `artifact hash` as one of the eleven, which means it
  identifies the thing being described rather than the description.
- **An unfitted model has no hash, distinguishably.** The same distinction
  [[REQ-REPRO-001]] already draws between `NO_MODEL` and `UNRECORDED`, and the
  same one three requirements today have each had to make: absent and zero must
  not read alike.
- **Deployment status is recorded, not acted on.** Deciding promotion belongs to
  [[REQ-EXP-008]] and the gate; this stores what was decided.

## What is still open

- **What exactly is hashed for a model whose state is numpy arrays** is a design
  question for the plan. A hash over floating-point bytes is exact and brittle;
  a hash over rounded values is stable and lossy. Which is right depends on
  whether two runs that differ in the last bit are the same model, and that is
  not obvious.
- **Serving the registry over the API is out of scope**, and this is not the
  pattern three requirements today have warned about: the consumer is the
  experiment registry, which cites an artifact hash the moment one exists — a
  real consumer in the same repository rather than a promised one.
