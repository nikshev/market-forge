---
id: OUT-2026-09-09-spec-scored-markets
step: spec
records: [REQ-US-001, REQ-US-004]
commit: null
---

## What was done

`specs/026-scored-markets/spec.md`: two user stories, 11 functional
requirements, 9 success criteria.

## What was decided

- **Both stories in one spec.** They are one surface over one score, and
  splitting them would have built the repository's score storage twice.
- **The unscored market's place is stated.** Neither story's one-line acceptance
  settles it, and the answer decides whether a market nobody scored appears
  among the worst setups.
- **A missing family never becomes a negative factor.** [[ADR-044]] made that
  distinction in the score; the panel is where a reader would lose it.
- **The explanation stays out of the outcome object**, per PRD §27.4.

## What is still open

- **The pipeline does not yet write scores.** The API reads what was stored, as
  it does for every other endpoint; producing a live score per market is
  pipeline work.
