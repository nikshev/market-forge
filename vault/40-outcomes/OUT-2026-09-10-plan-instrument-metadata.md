---
id: OUT-2026-09-10-plan-instrument-metadata
step: plan
records: [REQ-WP-021]
commit: null
---

## What was done

`specs/060-instrument-metadata/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/normalizer.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-021]] moves to `planned`.

## What was decided

- **A bad rule is refused in the value's constructor**, not at the point of use.
  A rule is consumed far from where it was parsed; validating at use means every
  consumer has to remember, and the one that forgets rounds a price to a tick of
  zero and produces a number. Validating in the constructor means the bad value
  never exists — and it covers every construction path, including a row read
  back and a second venue's normalizer.
- **Zero marks "no rules yet" on a plane that has no null.** It is the one value
  `Instrument` itself refuses, so a row carrying it cannot be mistaken for a
  real instrument.
- **The latest row wins for a market described twice**, on both implementations.
  The plane is append-only, so a re-ingest is two rows, and returning both would
  make a routine refresh look like a second venue. The in-memory repository is
  keyed by `(venue, symbol)` so the two cannot drift.
- **A float is refused rather than converted.** `Decimal(0.1)` is not refused by
  Python and is not the venue's tick size.

## What is still open

- **The schema fingerprint of the `markets` table changed.** Nothing is
  invalidated because no dataset reference cites that table — true now rather
  than by design, and a later table would not be so free.
