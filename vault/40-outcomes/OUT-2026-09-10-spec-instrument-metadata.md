---
id: OUT-2026-09-10-spec-instrument-metadata
step: spec
records: [REQ-WP-021]
commit: null
---

## What was done

`specs/060-instrument-metadata/spec.md`: three user stories, 12 functional
requirements, 8 success criteria. [[REQ-WP-021]] moves to `specified`.

## What was decided

- **A missing rule is refused; a missing record reads as absent.** Two halves of
  one rule, and both exist so an unknown tick size and a tick size of zero never
  look alike.
- **A spot instrument has no contract size**, rather than a contract size of one.
  Storing `1` would let a later calculation multiply by it and be right by
  accident, which is a worse failure than being wrong.
- **A duplicate symbol in a payload: the later entry wins**, stated rather than
  left to whichever data structure the implementation reaches for.
- **The consumer ships with the store.** The API serves an instrument's rules the
  moment they are stored, because three requirements here have each recorded the
  same pattern of a mechanism nobody used.

## What is still open

- **Whether these five fields are "basic" is a judgement**, and the PRD neither
  confirms nor contradicts it. The derivation is written out so a disagreement
  has something to argue with rather than a preference to assert against.
- **Only Binance's payload shape is normalized**, because it is the only
  connector. A second venue is a second normalizer, and whether the value type
  survives contact with a venue that expresses its rules differently is not
  knowable from one example.
