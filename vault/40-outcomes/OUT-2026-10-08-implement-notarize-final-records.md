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

**Stage 2 -- the live deployment (T035–T042):** _not yet performed when this stage was committed._

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

## What is still open

- The live phase: the secrets directory for uid 10001, the build from a clean committed tree, starting the
  `notary`, the first confirmed batch, the measurement (50+ records, 3+ series, 1+ hour), the outage drill.
- `docs/notary.md` says "not yet measured"; a test makes that true until `deployments/monad-testnet-latency.json`
  exists and then makes the text quote it exactly.
- The suppression kind has no live producer (the worker delivers no alerts); its schema and tests exist.
