---
id: OUT-2026-09-08-spec-volume-profile
step: spec
records: [REQ-WP-012]
commit: null
---

## What was done

`specs/017-volume-profile/spec.md`: five user stories, 14 functional
requirements, 9 success criteria, one ADR.

## What was decided

- **The value area is grown from the POC, taking the larger neighbour**
  ([[ADR-028]]). PRD §14.1 gives the target share and not the construction, and
  the plausible alternatives differ: taking bins by descending volume reaches
  70% faster but need not be contiguous, and a narrowest-window search need not
  contain the POC at all. Both differences appear on a bimodal profile, which
  is the shape that matters.
- **A "target not met" flag travels with the result.** A value area equal to
  the whole profile looks like a wide market; it may instead mean the profile
  had four bins.
- **§14.2's VWAP family and §14.3's volume anomaly are out of scope** — neither
  is in REQ-WP-012's acceptance criteria.
- **Profile windows are the caller's.** §14.1 lists rolling 4h/24h/7d and
  anchored sessions; the builder takes a trade list, so those are all the
  caller choosing what to pass. The anchoring rules are not built.

## What is still open

- Nothing from this step.
