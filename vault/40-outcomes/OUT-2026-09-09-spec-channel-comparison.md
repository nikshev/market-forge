---
id: OUT-2026-09-09-spec-channel-comparison
step: spec
records: [REQ-EXP-001]
commit: null
---

## What was done

`specs/034-channel-comparison/spec.md`: three user stories, 14 functional
requirements, 10 success criteria.

## What was decided

- **The seven metrics get definitions**, each stated where it is computed, so a
  reader can disagree with the definition rather than with a number.
- **Cost is an operation count** ([[ADR-049]]).
- **The rejection rule is fixed across models.** EXP-001 compares channels, not
  exit policies.
- **A model's refusal is reported, not fatal.**

## What is still open

- **Coverage is measured against the band as it stood**, not projected along the
  channel's slope. PRD §13.7's forecast channel is where that belongs, and
  `ChannelSnapshot` does not carry the raw log slope.
