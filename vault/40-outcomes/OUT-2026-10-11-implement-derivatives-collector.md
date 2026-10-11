---
id: OUT-2026-10-11-implement-derivatives-collector
step: implement
records: [REQ-WP-093]
commit: null
---

## What was done

Implemented [[REQ-WP-093]] as far as the repository goes (tasks T001-T016 of `specs/145-derivatives-collector/tasks.md`;
T017-T020 are the live steps and follow the deployment). Status is `tested`, not `implemented`: SC-001 (the panes enabled
on the running stack after a day of collection), SC-005 and SC-006 are measurements of the deployed system and are
recorded when it has run.

- **The collector**: `channelflow.context` (`sources`, `rest`, `pollers`, `runtime`, `status`) and
  `pipeline/context_main.py`; three compose services (`context-binance`, `-bybit`, `-okx`) with a healthcheck on
  `/healthz`, a Prometheus job, `.env.example`, `docs/deployment.md`.
- **The table**: `tables/derivatives_state.py` (PRD §10.4 + source + both times; a sink that stores each observation
  once, across a restart), added to the maintenance service.
- **The normalizers**: Binance (`futures_state`, `open_interest_state` -- two states, because the two answers are about
  two instants -- and `funding_history`), Bybit (the venue's own time, `funding_history`) and OKX (`funding_history`
  with the realized rate); the three registrations now say where each number comes from and when it is stale.
- **The worker pass**: the pure evaluation in `features/context_values.py` and the table side in
  `pipeline/context_pass.py`, one call beside `write_flow_features`.
- **Mutation sweeps**: nine files, 77 mutations; every survivor is either killed by a test added for it or carries a
  reason (below).

## Evidence

**RED first.** The tests were written before any module existed; the first run, before `channelflow.context` was
created:

    ImportError while loading conftest '.../tests/unit/context/conftest.py'.
    ModuleNotFoundError: No module named 'channelflow.context'

**GREEN.** After the implementation: the new tests and everything around them (connectors, tables, context, features,
pipeline, derivatives) 966 passed; `make lint`, `make typecheck` clean; the deployment-exposure test's count of
published ports moved from nine to twelve (the three collectors, loopback by default) and says why.

**What the mutation sweeps found in the tests**, and which are now fixed:

- A state received **after** the close was used for basis (only open interest had a test): added.
- A state **dated** after the close but received before it -- a venue clock running ahead of ours -- was untested:
  added.
- A series with no configured perpetual was untested against states existing under its own name: added.
- A failing history load was retried only after an hour in the mutated code and no test noticed: added; asking again
  on the poll cadence is now pinned.
- A normalizer's refusal (a missing field) escaping as a crash instead of a failed poll, the number of Binance
  open-interest buckets asked for, and the history limit being too small for the 24-settlement window: tests added.

**Survivors that are equivalent**, each with its reason in the `.toml`: the history rows also being offered to the
polled list (every polled read skips a state without the field it needs); slicing the funding history at the close
(`settled_funding` is the guard that matters; this is defence in depth); the per-series versus per-feature watermark
(differs only with a mid-range gap in one feature, which no fixture has); a few venue-error paths that the shape
checks refuse for the same outcome; and two conventions (404 for an unknown path, the market-type column).

## What was decided / found along the way

- **A state is used only if the collector had received it by the close** as well as its event time being at or before it.
  The spec said event time; the test for Binance's open-interest bucket, which is dated at its own time and lands
  later, showed that event time alone would let a feature use something not yet seen. Settled funding is the exception:
  it is public from its settlement however long afterwards the history was loaded, so it is held to its event time.
- **OKX's `contract_value` already existed** with a different signature; the first draft redefined it (ruff caught the
  shadowing) and was replaced by a call to the existing one.
- **`tests/unit/context/doubles.py`** holds the fake HTTP client; `conftest.py` imports from it, because importing
  from a conftest is not a thing `tests` as a package supports.
- **Iceberg appends here retry and land**, so ADR-070's claim that two writers would conflict at commit was wrong; the
  ADR was corrected before it was committed to say the reasons for one writer are about where a feature is computed.

- **`features/` may not reach for a storage backend** (PRD §29.0). The first version of the pass lived in
  `features/` and the isolation test refused it; it was split, as CVD's was: the pure as-of evaluation stays in
  `features/`, the reading and writing of tables is in `pipeline/`. Found by `make graph`'s full run, not by the
  tests written for the feature, which is what the full run is for.

## The replay on the real lakehouse (T017) and the first deployment

**Replay, nothing written** (the table's `append` replaced by a recorder, in the collector's container, with the
live stored states): 150,251 bars read in 9 s; the pass computed **83,132 rows in 6.1 s**. `funding_z` appears for
the span after the 24th settlement of the 50 each venue returned (about 8.7 days of one-minute bars per series) and
its values lie in [-2.92, 2.21]. Five rows sampled at random from the Bybit one-minute series equal a plain-arithmetic
z-score of the last 24 stored settlements to the ninth digit. Open interest and basis exist only for bars after the
first poll (one bar at the time of the replay), which is right: the collectors had run for minutes.

**Deployment**: the three collectors started with `up -d --no-deps` and logged their first requests within a second;
each stored its first rows (50 settlements and the current state per symbol) and reported healthy; the start times of
all 27 existing containers were unchanged. The worker and the notary were then rebuilt from the clean commit
(`18415c1`) by the documented redeploy.

**What the first real pass taught**: the worker's first pass wrote one commit per series and spent minutes at 100%
CPU between commits with nothing in the log. Every append here computes the content hash of the whole table, so a
commit costs in proportion to the table, not to the rows added -- thirty-five commits for 83,000 rows is the better
part of an hour. The pass now makes one commit; the replay could not have shown this, because it replaced the
commit. The lesson is the one the 2026-10-08 incident wrote down, in a smaller key: a replay that stubs the write
proves the arithmetic and says nothing about the cost of the write.

## What is still open

- **Not yet run against the real lakehouse**: the worker pass has to be replayed on a copy of it without writing before
  the worker is rebuilt (T017), and the collectors have to run for a while to have anything to read.
- **Worker rebuild** deploys everything committed since 2026-10-08, not only this: the order is collectors first.
- Binance's open-interest bucket staleness (15 minutes) and the 3-minute bound are stated defaults; the measurement
  after deployment may show different ones are better.
