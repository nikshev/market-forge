---
id: OUT-2026-09-09-spec-ablation
step: spec
records: [REQ-US-006]
commit: null
---

## What was done

`specs/030-ablation/spec.md`: two user stories, 11 functional requirements, 9
success criteria.

## What was decided

- **An arm that could not look is never reported as having looked.** Two of
  REQ-US-006's five arms name families the registry does not carry, so without
  this the ablation reports "channel + DEX" scoring exactly what "channel only"
  scored.
- **The folds are the caller's**, built once. EXP-015 says "same walk-forward
  folds" in as many words.
- **One scoring path**, the direct baseline's, so an arm's score means what
  REQ-WP-019's does.

## What is still open

- **No channel or DEX features are registered.** Until they are, three of the
  five arms report as not run — which is the honest state and is visible.
