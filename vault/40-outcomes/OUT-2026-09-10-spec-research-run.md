---
id: OUT-2026-09-10-spec-research-run
step: spec
records: [REQ-WP-024]
commit: null
---

## What was done

`specs/063-research-run/spec.md`: three user stories, 12 functional
requirements, 9 success criteria. [[REQ-WP-024]] moves to `specified`.

## What was decided

- **The comparison reports what it fitted.** The alternative — refit to obtain a
  hash — is a second scoring path, which this repository has refused wherever it
  has come up. `Score` gains an optional artifact so the two experiments that
  supply their own predictions report none rather than a false one.
- **A variant's artifact covers its folds together**, because what a result cites
  is the variant as run. Per-fold registrations would be artifacts nothing cites,
  and the run's own identity would be ambiguous between them.
- **The refusals are part of the acceptance.** This spec adds no mechanism, so
  its characteristic failure is a happy path that proves nothing: four hashes
  assembled and never refused would satisfy a careless reading while leaving every
  refusal as theoretical as it was. FR-007, FR-008, FR-011 and FR-012 are there
  for that, and the success criteria require a refusal to name what stopped it.
- **"Changes when a fold changes and not otherwise"** is written into SC-002
  deliberately: a combined hash sensitive to fold order, or to an unrelated
  variant, would pass a looser reading and make two identical runs look different.

## What is still open

- **Adding a field to `Score` changes its equality**, and several callers read it.
  Optional with a default should keep every existing test true; how many break is
  not known until it is done, and it is the main risk to the shape.
- **Whether one experiment's path generalises** is unknown by construction. If the
  second caller needs a different path, that is a finding about the path rather
  than about the second experiment.
