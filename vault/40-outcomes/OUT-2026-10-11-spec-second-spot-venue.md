---
id: OUT-2026-10-11-spec-second-spot-venue
step: spec
records: [REQ-WP-098]
commit: null
---

## What was done

Specified and planned [[REQ-WP-098]] (spec 150) in one step: the owner, shown the Binance spot venue-basis pane
reading "only 1 venue(s) could contribute", chose a second spot venue. The spec, plan and tasks are in
`specs/150-second-spot-venue/`.

## What was decided

- **OKX spot**, because the project already ingests OKX, has its connector, normalizers and market-type rule
  (`BASE-QUOTE` is spot), and OKX lists the same three pairs. No new venue code, only configuration and one rule.
- **The one list of series** (`context/sources.py`'s `SERIES`) from which each venue's book symbols derive, with the
  perpetual mapping kept explicit and checked against it. Rejected: deriving a spot pair's perpetual from its
  spelling (a fact about OKX in code that would be wrong for the next venue).
- **Kind by instrument**: OKX serves spot and swaps from one endpoint and their sizes mean different things (base
  units against contracts), so the book asks the instrument.
- **No change to the consensus maths or the API.**

## What is still open

- The worker's cycle grows with three more series; to be measured, not designed away.
- Whether a third spot venue or Bybit spot is wanted: not asked for.
