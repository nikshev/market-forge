---
id: OUT-2026-09-10-implement-extremum-markers
step: implement
records: [REQ-WP-028, REQ-PHASE-1A]
commit: null
---

## What was done

Four layers: `tables/extrema.py`, both repositories, `GET /api/v1/extrema`, and
`extrema.ts` deciding the markers the chart draws.

29 new tests (19 Python, 10 TypeScript), 1626 in the Python suite and 73 in the
web one, mypy clean at 169 files, typecheck and build clean, **16 of 16 mutants
caught across both halves**.

[[REQ-PHASE-1A]]'s last unbuilt deliverable is closed and the phase reaches
`implemented` — **the sixth**, after Phases 6, 0, 1, 7 and 2.

## What the sweep confirmed

The pair that matters held on both sides. Drawing a confirmation at its
`known_at` instead of its `extremum_time` **never appears too early** — it
satisfies PRD §45's criterion word for word and puts the turn in the wrong
place. Only asserting both halves catches it, and both mutants were caught.

The other one worth naming: keying the table's event time on the turn's own
instant instead of on `known_at_ns`. That single change turns every
point-in-time read into a repaint, and it is a one-word edit in a schema.

## What is still open

- **Nothing writes extrema yet.** The detector produces them and no pipeline
  stores them; the tables and the endpoint are reachable and empty. This is the
  pattern five requirements have recorded before, and it is named here rather
  than left to be discovered: a replay that ran the detector and wrote its output
  is the missing caller, and it belongs with whoever wires [[REQ-PIPE-001]]'s
  replay to the detector.
- **I cannot see the markers.** Confirmed turns draw filled and candidates
  hollow with a `?`; both are honest and a reviewer may want another answer.
- **The in-memory repository restates the rule by hand.** The conformance suite
  is the only thing keeping the two implementations equal on it.
