---
id: OUT-2026-09-11-spec-iceberg
step: spec
records: [REQ-WP-039]
commit: null
---

## What was done

`specs/077-iceberg/spec.md`: five user stories, 10 functional requirements,
7 success criteria. [[REQ-WP-039]] moves to `specified`.

## What was decided

- **The spec is organised around the failure mode, not the feature.** A
  migration does not fail by crashing; it fails by arriving with a working
  Iceberg table that has quietly stopped doing one of nine things. Each user
  story is one of those things, and the dangerous ones are the quiet ones — a
  point-in-time read that silently includes later rows still returns a table.
- **SC-007 is the criterion that cannot be faked.** Six criteria each check one
  property; the seventh checks that none was forgotten. It is the only one a
  correct-looking migration with a dropped guarantee would fail.
- **The point-in-time question is left open on purpose.** Iceberg offers a
  snapshot lookup and a row filter over event time, and they answer differently
  when a commit carries rows older than its predecessor — which this system's
  replays do. The plan measures it. Guessing is what the last two requirements
  paid for twice.

## What is still open

- **Which mechanism serves point-in-time reads**, as above.
- **Where the catalog lives on the stack**, and who creates the namespace.
- **The old format is still here.** This step adds; removal is a later step, and
  the requirement stays open until the last caller moves.
