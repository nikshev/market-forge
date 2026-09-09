---
id: OUT-2026-09-09-spec-channel-baselines
step: spec
records: [REQ-CHAN-001]
commit: null
---

## What was done

`specs/032-channel-baselines/spec.md`: three user stories, 15 functional
requirements, 11 success criteria. A new requirement note, because
[[REQ-EXP-001]] compares five channel models and PRD §13.3 to §13.5 had none.

## What was decided

- **§13.5's prohibition becomes structure.** "Uses only past observations" is
  what a recursive loop can carry and a comment cannot.
- **Theil-Sen and RANSAC are named as unbuilt.** §13.3 lists three candidates;
  a module silent about the other two reads as the section, implemented.
- **Quality is reported in each model's own terms.** Baseline A's coverage
  submetrics do not transfer to conditional quantiles or to a filtered level.
- **§13.6's experimental trend filter is out of scope**, and the note says why.

## What is still open

- **Two of §13.3's three estimators.** Named, not built.
