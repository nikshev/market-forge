---
id: OUT-2026-09-10-requirement-instrument-metadata
step: requirement
records: [REQ-WP-021]
commit: null
---

## What was done

[[REQ-WP-021]] extracted by hand from PRD §45's Phase 1 deliverable list. It is
the last of Phase 1's twelve deliverables with nothing behind it and the only
entry in [[REQ-PHASE-1]]'s `not_delivered`.

## What was decided

- **"Basic" is derived from what breaks without it, not from what exchanges
  publish.** A venue's instrument payload has dozens of fields. The five kept
  are each there because something downstream cannot be correct without them: a
  fill at a price the venue cannot quote is a fill at a price that does not
  exist, and a position below the minimum notional is not a trade anybody could
  place. PRD §41 rule 9 governs any economic evaluation, which is what makes
  this a correctness field rather than a display one.
- **A missing field is a refusal, not a default.** A tick size guessed at is
  worse than one absent: absent stops a calculation, and a guess produces a
  number that looks like a measurement.
- **Using the rules is out of scope, and the note says so.** Rounding a fill to
  a valid tick, refusing a size below the minimum, skipping a halted instrument —
  each changes the backtest's execution model and deserves its own requirement.
- **The API serves them the moment they are stored.** This is the fourth time
  this session a mechanism could have been built with nothing using it
  ([[REQ-STORE-001]], [[REQ-TBL-001]], [[REQ-BIAS-011]] each recorded that
  pattern in turn). Serving through the existing markets endpoint is what stops
  it happening again here.
- **HTTP is out of scope.** [[REQ-WP-003]] keeps the wire behind a `Transport`
  protocol; the normalizer takes a payload and where it came from is the
  caller's business.

## What is still open

- **The chosen five fields are a judgement about "basic".** Nothing in the PRD
  confirms or contradicts them, and a reader who thinks tick size is not basic,
  or that funding interval is, has as much textual support as this note does.
  The derivation is written out so that disagreement has something to argue
  with.
- **Extending the `markets` table changes its schema fingerprint.** No dataset
  reference cites that table today, so nothing is invalidated — but that is true
  now rather than by design, and a later table would not be so free.
