---
id: OUT-2026-09-09-spec-stop-policy-comparison
step: spec
records: [REQ-EXP-017]
commit: null
---

## What was done

`specs/050-stop-policy-comparison/spec.md`: three user stories, 15 functional
requirements, 15 success criteria.

## What was decided

- **Every policy replays the same entries**, and the entry set carries a
  fingerprint so a cross-report comparison is checkable rather than asserted.
- **The premature-stop rate is a property of the object that carries realized
  expectancy** — PRD §44A.29's warning made structural.
- **An ablation delta may be negative.** Some capabilities do not earn their
  place, and an experiment that assumed otherwise has nowhere to put that.
- **The verdict excludes the engine from its own rivals**, because an engine
  counted among them is the best of them by construction.

## What is still open

- **The entries, paths and anchors are supplied.** This experiment manages what
  happens after an entry; producing entries belongs to the signal layer.
