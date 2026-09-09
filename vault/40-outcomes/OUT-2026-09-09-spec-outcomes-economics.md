---
id: OUT-2026-09-09-spec-outcomes-economics
step: spec
records: [REQ-BT-001]
commit: null
---

## What was done

`specs/033-outcomes-economics/spec.md`: three user stories, 17 functional
requirements, 12 success criteria. A new requirement note, extracted because
nine of the seventeen experiments are blocked on the same three PRD sections.

## What was decided

- **The ambiguous case is the requirement's centre**, not an edge case. §40
  emphasises it, and both readings of a both-touched bar look plausible.
- **A touch includes equality.** A strict breach is the favourable ordering by a
  tick, on every trade.
- **The cost model is a required argument** ([[ADR-048]]), which is [[ADR-009]]'s
  reasoning kept rather than dropped.
- **Targets and stops are supplied.** An outcome resolver that invented either
  would be scoring its own choices.

## What is still open

- **§25.4's phase-2 fills** — trade-through and L2-aware — need book state a bar
  series does not carry.
