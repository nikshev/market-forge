---
id: OUT-2026-10-08-implement-notarize-final-records
step: implement
records: [REQ-INFRA-007]
commit: null
---

## What was done

Implemented [[REQ-INFRA-007]] in two stages with the live deployment between them (tasks T001–T042 in
`specs/143-notarize-final-records/tasks.md`).

**Stage 1 -- everything that needs no running stack (T001–T034), `status: tested`.** The package
`src/channelflow/notary/` (2,218 lines: `scheme`, `records`, `context`, `tables`, `registrar`, `batcher`,
`submitter`, `chain`, `verify`, `latency`, `config`, `main`), 186 tests in `tests/notary/`, five mutation
specs in `tests/mutations/`, the compose `notary` service with its secrets, the Dockerfile build arguments, the
Prometheus job, `make notary-build-info`, `docs/notary.md` and the deployment section. The worker's pass now
registers what it computes; nothing else about the pass changed.

**Stage 2 -- the live deployment (T035–T042), `status: implemented`.** Done on 2026-10-08 against the running stack and Monad testnet; the evidence and what went wrong on the way are below.

### RED, before the code

Each test group was written before the module it exercises and run first; every first run failed for the
right reason -- the module did not exist (`ModuleNotFoundError: No module named 'channelflow.notary'`, later
`…notary.registrar`, `…notary.batcher`, `…notary.submitter`, `…notary.verify`, `…notary.latency`,
`…notary.main`), and the compose tests failed on assertions about a service that was not there (5 of 6
failing; the sixth, "no key-shaped environment value", passed trivially, which is the nature of a
negative guard). The first run of the core groups, saved as it happened, was `4 errors during collection`.

Two groups were written **after** their code and are said so: the operation-count test of the pass
(`test_the_notary_adds_one_read_to_a_pass_…`) and the end-to-end outage test. Their value is checked by the
mutation specs, not by a RED run.

### Mutation specs (the repository's acceptance audit)

| Spec | Caught | Survived | Survivors |
|---|---|---|---|
| `notary_scheme` (hash framing, tree, proof verifier) | 13 | 3 | all three **equivalent**: guards in the verifier (index range, path length, exhaustion) that the final root comparison also enforces, short of a SHA-256 collision; reasons recorded in the spec |
| `notary_records` (refusals, verdicts, identity) | 8 | 0 | |
| `notary_context` (commit, dirty tree, config fields, state vs config) | 7 | 0 | |
| `notary_batcher` (window, cap, order, whole second, orphan repair) | 8 | 1 | **equivalent**: the contiguity check of orphan repair is covered by the root check beside it |
| `notary_submitter` (reconcile-before-send, finalized, order, limits) | 11 | 0 | |

The first run of the batcher and submitter specs left **five** survivors; four were real gaps and are now
tests: a transaction still in flight must not be sent again before its timeout; a transaction mined as a
revert after the process stopped looking must be noticed; a batch that cannot be sent must hold those
behind it (the first version of that test held both batches with the same global limit and so proved
nothing); orphaned leaves that do not hash to their root must not become a batch.

## What was decided

Changes to the plan made while implementing, each because something was measured or broke:

- **Registration is a subscription on the bus, not a hook on the recorder** (plan decision 2, revised). The
  pass replays all history every cycle and `record_replay` already takes a caller's bus, so the registrar needs
  no change to `replay.py` and heals itself: a crash between the lakehouse write and the registration is
  repaired by the next cycle, tested by registering nothing, "crashing", and running again.
- **The config hash is an explicit list of fields, with a completeness test** (research R8). `SignalMachine`
  holds mutable state (`candidate`, `_awaiting_zone_exit`) beside its parameters; a recursive walk would have
  hashed the state and given every bar a different hash. A test enumerates every field of every component
  and fails unless each is classified as configuration or state. Found by reading the objects, not by a bug.
- **An unclassified nested component is named, not hashed half-way.** The first version let an unknown
  detector fall through to a less precise error; a test of that case found it.
- **Monad charges the gas limit** (measured on the chain, research R4): a commit sent with a limit 40 % over
  the estimate cost exactly 40 % more, and the receipt reports the limit as gas used. The signer's limit is
  the estimate times 1.05, nothing more.
- **The pass-time bound was the wrong shape and was replaced** by an operation count (at most one extra read,
  at most one extra commit per series-timeframe, no other table read more often) plus a recorded timing.
  Measured on a 120-bar fixture: 0.38 s → 0.45 s, **+66 ms per series-timeframe** (a fixed cost: one commit
  and one read), ≈ 0.2 % of a live pass of 17–21 minutes.
- **The oldest-pending age is of the oldest unconfirmed record from its registration**, not of its batch from
  its formation: the first version reset the clock whenever a batch was formed, which would have hidden a
  stuck record. Found by an outbox test that expected the wait to be visible.
- **A guard in an existing test was refined, not bypassed**: `test_no_credential_is_written_into_the_compose_file`
  now accepts a `/run/secrets/…` path as a reference, because a mounted secret's path is not the secret; the
  `.env.example` guard accepts an EVM address (0x + 40 hex) and still refuses a private key's 64-hex shape.
  Two counters/parsers in repository tests were updated for the new port and the new top-level `secrets:`
  section.

## Findings about the existing system (not fixed here)

1. **`SignalRecorder` freezes a candidate at first sight** and never appends its later transitions: 341 of 422
   non-terminal signals were older than 24 hours, 294 of them still `approach` with one transition. Anything
   reading `signals` or `signal_transitions` (the API, the chart) shows stale states. The notary does not
   depend on it, and a test demonstrates it on real replay output (the table holds one transition, the
   notary registered the whole history). **A candidate requirement for the owner to accept or decline.**
2. **A worker cycle is 28–35 minutes** (channel part 17–21 minutes, a flow step of 10–14 minutes, 5 minutes of
   sleep), because every series replays its whole history and `watermark()` reads whole tables, all five
   tables, per series-timeframe. A 5-minute snapshot reaches the lakehouse up to ~35 minutes after its bar
   closed; the notary adds the batch window on top. The figure the product may quote will say so.
3. **`ChannelSnapshot`'s window fields are not persisted** (`window_bars`, `window_short`,
   `first_bar_after_gap_ns` have no columns), so they are not in a notarized snapshot's bytes. Same family
   as the `confirmation_lag_ns` gap found earlier.
4. **`window.py` passes the literal `threshold=1` to `is_gap`**, so `CHANNELFLOW_GAP_THRESHOLD` does not change
   the channel window; it is in the config hash because it is the configured value.

## Live deployment (stage 2)

**Setup (T035, T036).** The keystore and its password were copied to `/root/.monad/runtime/` owned by uid 10001, mode
400, outside the repository, and mounted by compose as files; read back as that uid. The images were built from clean
committed trees with the commit baked in. Only `worker` and `notary` were recreated; the start times of every other
container were identical before and after (a diff of `docker inspect`). The worker has no `/run/secrets`; the notary
logs its signing address, equal to the contract's `owner()` (it refuses to start otherwise). The stable settings
(`CHANNELFLOW_NOTARY_ENABLED`, the epoch, the key paths, the contract address and deploy block) were appended to the
local `.env` after a backup; **the commit and the dirty flag are deliberately not in it** -- a stale value there would
label new records with code they were not produced by.

**First real batch (T037).** Block 69321381, tx
[`0x32b1f746…3a00`](https://testnet.monadvision.com/tx/0x32b1f7461ef153e582a3fff61a6436ee2c5468efe0713843be0cbb9037323a00),
root `e8b9b461…efbdf9`, 113 records. A snapshot and a decision from it were verified with `verify check` (committed,
bar close to block, the "no later than" sentence). A bundle exported for the snapshot was then verified **in an empty
environment** with nothing but the file and the public node: `committed`; with one byte of the record changed:
`not committed -- the record hash does not match the record and its context`.

**Measurement (T038).** `deployments/monad-testnet-latency.json`: **168 records, 5 series, 3,917 s of block times**
(the criterion was 50+, 3+, 3,600 s). Per record, bar close to block: **median 5,653 s (94 minutes), p95 6,553 s,
max 6,870 s.** The first batch was set aside: its records had been registered about 1.5 hours late because of the
worker failure below, which is not what the path costs in steady state. The delay is the whole path, not the
notary's: `resample` leaves the 5-minute series about 45 minutes behind the clock, the worker's cycle is 28–35
minutes, the batch window adds up to 30. `docs/notary.md` quotes the file; a test enforces it.

**Outage drill (T039).** `notary` was stopped at 19:41:51 for 30 minutes while the worker kept running. During it:
the outbox grew from 9 to 72 unbatched records and the oldest waited 1,932 s (visible from the `outbox` command, no
chain and no key needed); the worker completed a pass with 0 `FAILED`; **no transaction was sent** (account nonce
8 -> 8). After the restart the backlog became **one** batch of 72 records, **one** transaction (nonce 8 -> 9),
confirmed at block 69347060. Across all five batches every root was submitted exactly once and no record is in two
batches (353 unique ids in 353 leaves). This drill stops the *process*; "the chain is unreachable while the process
runs" is covered by the submitter tests and the end-to-end outage test, not by this drill.

**Cost (T040).** Five batch commits took the balance from 4.912557 to 4.869990 MON: **0.00851 MON each** (79,455
estimated gas x 1.05 margin x ~103 gwei). At the configured ceiling of 48 commits a day that is 0.41 MON a day, so
the 4.87 MON now held lasts about **12 days**, as planned. The gas-limit experiment (T002) cost 0.0115 MON.

## What went wrong on the way (all found by looking at the running system, none by the suite)

1. **I broke production channel output for about 70 minutes.** Rebuilding the `worker` image shipped REQ-WP-087's
   gap policy -- implemented on 7 October and never deployed -- and on real data every hole leaves a window of one
   bar, which `np.polyfit` cannot fit. Every series then failed with `LinAlgError`. I noticed after thirty minutes
   of silence from the notary, not from the worker's log, which is where the first sign was. Fixed by a floor on
   the window (`min_window_bars`, default 10), verified on the real lakehouse before deploying; see
   [[OUT-2026-10-08-implement-gap-window-floor]]. The deploy procedure now says to read the worker's log for
   `FAILED` first.
2. **`eth_getLogs` is limited to 100 blocks on the public node.** The first real commit succeeded and could not be
   confirmed, because the evidence search started at the deployment block, 104,000 blocks back. The test chain had
   no such limit, so every test passed. Evidence is now found from the commit's own time by bisection, in windows of
   at most 100 blocks (39 calls against the real chain); a transaction the service sent itself is confirmed from
   its receipt and needs no search; and the test node enforces the limit.
3. **My own deploy command moved the epoch.** `make notary-build-info` printed `CHANNELFLOW_NOTARY_FROM`, so
   evaluating it exported a value that overrode `.env` and moved the epoch forward by over an hour, which would
   have left those records unregistered for good. The epoch was restored from `.env` before it cost any, and the
   target no longer prints it; a test asserts that.
4. **Two of my own monitoring commands were silently wrong** (`cut` buffering a pipe; `docker exec` without `-i`
   dropping a script's stdin). Both reported silence where there was information. Silence from a monitor is now
   treated as a reason to look, not a reason to wait.

5. **The outbox summary read the records table twice** and failed with a `KeyError` whenever the worker registered
   a record in between -- 253 times in the three days after the deployment, found on 2026-10-11 by reading the
   notary's log, not by a test. No commit was affected (the tick had already run), but the gauges were not updated on
   those ticks and the `outbox` command could fail the same way. Each table is now read once and the waiting set is
   derived from those rows ([[REQ-INFRA-007]], commit `978f18d`); two tests reproduce it (a record registered
   between the reads; the table read exactly once). The same afternoon showed the system as it had held up over
   three days: 99 batches committed, each root once, balance 4.03 MON (the planned ~0.34 MON a day), and the
   24-hour latency (2,495 records) at a median of 3,672 s, better than the 5,653 s first measured -- the upstream
   lag varies, so the figure in `docs/notary.md` is a measurement of one afternoon, labelled as such.

## What is still open

- **Latency is minutes-to-hours and mostly not the notary's.** If the product wants "within minutes" the work is
  upstream: `resample` lag and the worker cycle (each series replays its whole history, `watermark()` reads whole
  tables). A shorter batch window cannot help while records arrive in clumps once per cycle.
- **The floor of 10 bars** after a hole is a choice (see the gap-floor note); the owner may want another.
- **`SignalRecorder` freezes a candidate at first sight** (finding 1 of stage 1); the notary does not depend on it.
- **The suppression kind has no live producer**: the worker delivers no alerts, which also means [[REQ-INFRA-008]]
  (an alert that links to its transaction) starts from "there is no alert yet".
- **The owner key is one key on one host**, and the plain-text copy `/root/.monad/deployer.env` still exists
  (outside the repository, never read by the tools). Testnet only; deleting it is the key owner's decision.
- **CI is red for an unrelated reason** (the MinIO image pull); the new tests run in the fast gate regardless.
- The anvil rehearsal and the live deployment produced the same contract address (it is a function of deployer and
  nonce); nothing from the rehearsal reached the repository.
