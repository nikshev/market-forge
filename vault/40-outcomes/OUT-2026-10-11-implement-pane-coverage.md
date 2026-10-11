---
id: OUT-2026-10-11-implement-pane-coverage
step: implement
records: [REQ-WP-097]
commit: null
---

## What was done

Implemented the tool half of [[REQ-WP-097]] (spec 149): `tools/panes/` and `make panes-report`, a read-only report of
the state of every lower pane of every market against the running API. Status is `tested`; `implemented` needs the
recorded run on the deployed stack, which needs the worker rebuilt (T005).

- The three states (`data`, `absent` with a reason the system gave, `no-producer`) are decided by a pure function over
  the API's answers and tested offline; the pane list is read from the page's own `panes.ts`.
- Exit 0 / 1 / 2: every cell reasoned; some cell has no producer; the API could not be read.
- **Mutation sweeps**: two files, 20 mutations, all caught.

## Evidence

**RED first**: `tests/tools/panes` was written before `tools/panes` existed (an import error at collection).

**Run against the live API before the worker was rebuilt** (2026-10-11, the collectors a few hours old): open interest,
funding (z) and basis were `data` for every series; OFI, depth imbalance, liquidations and venue basis were
`no-producer` -- correctly, because the worker that writes them had not been rebuilt with the new passes -- and the DEX
panes `absent: no DEX source`. The tool said what the page showed, which is its job.

## What was decided

- **The reasons come from the system**: the consensus read's stored refusal reasons, the presence of covered
  liquidation windows. The one exception, stated in the module, is the DEX panes' "no DEX source", because the API
  cannot say it has no DEX ingest.
- **A pane empty with nothing to say is a failure, not a note**: exit 1. That is the state the requirement removes.

## What is still open

- T005: after the worker rebuild and a day of collection, the recorded run in this note, the service listing with health
  and ages, the image revision, and screenshots (light and dark).
