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

## The deployed run (2026-10-11 ~15:00 CEST, interim: the collectors are four hours old)

Everything below was deployed from the clean commit `297cd4a`: `context-binance`, `context-bybit` and `context-okx`
(healthy; 0.3-1.4% of one core each), the worker and notary (rebuilt by the documented redeploy; the notary's outbox
shows 0 unnotarizable records), and the `api` and `web` containers, which had **not been rebuilt since 2026-10-04** and
therefore served neither the consensus route nor the pane row the page now has (found by this report: the venue-basis
read answered `404 Not Found`, which was the route and not the data).

`make panes-report` over 1m, 15m and 1h, 24 h back (15 markets x timeframes, 11 panes): **113 cells `data`**, the DEX
panes `absent: no DEX source`, the three Binance spot venue-basis cells `absent: only 1 venue(s) could contribute at
the close; a median over one venue is that venue's mid wearing a better name` -- and **11 cells `no-producer`**, all at
the 15m and 1h timeframes: OFI and depth imbalance (and liquidations at 1h) of Bybit, OKX and one Binance series.
At **1m every pane of every market has data or a stated reason, and for Bybit and OKX BTC all nine panes have data
including the venue basis.** The 11 are the higher timeframes whose bars `resample` has not yet built past the instant
the book streams began (it runs about 45 minutes behind); they are reported as `no-producer` because the report cannot,
and should not, excuse an empty cell by guessing why -- they are re-checked after the series has caught up and are not
counted as met until they are.

Screenshots, from the running page (`bybit BTCUSDT`, both themes): `docs/ui/panes-live-{light,dark}.png` (the pane row
with every pane but the DEX ones enabled -- the row the owner first saw reading "no data" on every pane) and
`docs/ui/panes-live-1m-{ofi,depth,oi,venue-basis,liquidations,funding}-dark.png` (a line from 12:45 UTC, when the
collectors started, aligned with the candles). The 15m lines have one or two points yet for the same reason.

## What is still open

- T005, remaining: the 24-hour mark (2026-10-12 ~10:45 UTC): a run with zero `no-producer` cells at 1m, 15m and 1h, and
  `implemented`.
