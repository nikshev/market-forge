---
id: OUT-2026-09-10-plan-record-extrema
step: plan
records: [REQ-WP-029]
commit: null
---

## What was done

`specs/067-record-extrema/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/recording.md`, `quickstart.md`. Constitution Check passes with no
violations. [[REQ-WP-029]] moves to `planned`.

## Did the bus survive a second producer?

**Yes, unchanged**, and the pre-commitment to report otherwise stands unused.
`subscribe` and `publish` took a second producer and two more consumers without
a line moving.

Worth stating plainly how weak that endorsement is: the second producer
publishes into the same bus instance, in the same thread, on the same pass. It
exercises the seam, not the hard parts of one. The property most likely to bite
later — a subscription made during a dispatch — never arose, because the
recorders subscribe before anything is published.

## What was decided

- **Detection gets its own pass.** The runner owns its loop and offers no
  per-bar hook; adding one so a detector could ride along would change a
  component with nothing to do with extrema, to save an iteration over a list
  already in memory.
- **Watermarks read knowledge, not the turn.** `known_at_ns` and
  `observed_at_ns` are what the tables are keyed by, so watermark and storage
  agree by construction. Reading the turn's instant would silently skip a
  confirmation that arrived late about an early turn, and only on a re-run.
- **The detector is not changed.** It accumulates candidates on a list of its
  own, so publishing per bar means noticing what it appended. That reads
  awkwardly and is the honest shape for a caller.

## What is still open

- **Nothing yet attaches these subscribers live.** The events exist and a replay
  publishes them; PRD §25.1's live mode still does not exist.
