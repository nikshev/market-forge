---
id: OUT-2026-10-04-tasks-chart-candidates-no-data
step: tasks
records: [REQ-WP-084]
commit: null
---

## What was done

21 tasks in seven phases, tests first (T002-T008 RED before any source), one phase per user story. All ten
functional requirements and four success criteria map to at least one task.

## What the analysis found, and how it was resolved

`speckit-analyze` over spec, plan and tasks: no constitution conflict, full coverage, one real contradiction and
four smaller findings. All five were fixed in the artifacts before this commit.

- **F1 (HIGH): the plan and the tasks disagreed about `includeCandidates`.** The plan (D2) made it a required
  parameter; the tasks gave it a default of `true`. The tasks were right: `extremumMarkers` has 13 existing
  test call sites (11 in `extrema.test.ts`, 2 in `time.test.ts`) asserting behaviour that must not change, and
  the existing tests are this project's regression contract. A required parameter would have meant editing all
  13. Resolved by amending plan D2 and research R2: the pure function defaults to `true` (it describes what is
  available at the instant), `Chart` always passes the switch, and T004 fails if `Chart` forgets.
- **F2 (LOW):** the plan promised a Python check that the pane list names registered features; it already
  exists (`test_pane_features.py`). The plan now says so.
- **F3 (MEDIUM):** "survives a reload" is wrong for a page that remembers nothing across a reload. Reworded to a
  refetch (timeframe round-trip, mode switch); T016, which was vague, now names the three Story 3 cases and
  requires each to have been RED.
- **F4 (LOW):** "switch on while the extrema request failed" had no test; added to T007.
- **F5 (LOW):** a vague reference to a REQ-NRT test family replaced by the rule it meant.

## What was decided

- The two P1 stories ship together; Story 1 alone would already remove the noise.
- Screenshots use a playwright-intercepted features response for the populated row, since the live table is
  empty; the live, un-stubbed row (all "no data") is shot as well and the note will say which is which.

## What is still open

- **The owner pointed out the data should already exist.** Checked on the live stack: `/features/snapshot`
  returns `{}`. The CVD code exists (`features/flow.py`) and ingest normalises every trade, but the trade goes
  only to the bar builder; nothing feeds the feature code or writes rows to the features table. So CVD is
  computable from what is ingested, and a requirement for that wiring is the next piece of work.
- **OFI is not**: PRD §15.3 defines it on top-of-book changes and ingest reads the trade stream only, so OFI
  and depth imbalance need a book subscription first. The earlier note that CVD and OFI could both be derived
  from stored trades was only half right.
- Until that lands, the live chart reads "no data" for every pane, which is true.

## Found afterwards: the volume pane is missing

PRD §27.3 lists nine panes and the first is **volume**. `apps/web/src/panes.ts` has nine entries and none is
volume; `depth_imbalance_10`, which §27.3 does not list, stands in its place, and the comment above `PANES`
("all nine are here") is wrong. Volume needs no feature: every bar carries `volume_base` and the page already
loads the bars. What each pane needs, checked against what ingest subscribes to (trades only: Binance aggTrade,
Bybit and OKX trades):

- volume: bars, available now;
- CVD: trades, available, but not wired into the feature code;
- OFI, depth imbalance: a top-of-book subscription, not there;
- OI, funding, basis, liquidations: derivatives feeds, not there;
- DEX swap imbalance, active liquidity: DEX ingest, not running in the compose stack.

REQ-WP-084 is not changed by this (it shows what exists); the volume pane and the CVD wiring are separate
requirements, and each feed group after them is its own.
