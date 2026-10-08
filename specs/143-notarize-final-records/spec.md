---
traces: [REQ-INFRA-007]
status: draft
---

# Feature Specification: Notarize every final channel snapshot and decision

**Feature Branch**: `143-notarize-final-records`

**Created**: 2026-10-08

**Status**: Draft

**Input**: [[REQ-INFRA-007]] — user-directed integration 2026-10-03; touches PRD §0.13 (reproducibility), §26.4 (alerting), §29.B (dataset identity). Principles I, II, III, VII, X, XI, XIV. Builds on [[REQ-INFRA-006]] (the deployed `SignalNotary` contract).

## Context

[[REQ-INFRA-006]] gave the system a write-once notary on Monad testnet. This feature is what *uses* it: after a
bar closes, each final channel snapshot and each decision — including a decision **not** to alert — is hashed
together with the three things Principle XI says a result is reproducible from, and the hash is committed. Then
"this signal existed in exactly this form at this block" is a claim anyone can check without trusting us.

### Facts read from the code and the chain (2026-10-08), not assumed

1. **The running worker is a periodic batch pass, not a bar-close event loop.** `pipeline/channel_main.py`
   `run_pass` repeats every `CHANNELFLOW_CHANNEL_INTERVAL` over every series in the bars table and writes
   `channel_snapshots`, `signals`, `signal_transitions` and extrema. "After a bar closes" therefore means *when
   the record became final in the lakehouse*, and the delay between a bar's close and the pass that records it is
   part of what is measured, not hidden.
2. **No record named NO ALERT exists today.** The nearest things are a candidate's terminal transitions
   (`INVALIDATED`, `EXPIRED`, with a reason) in `signal_transitions`, and `AuditRecord(status="suppressed")` for
   an alert the freshness gate held back. PRD §0/§2 promise "NO ALERT, with a reason"; nothing persists one.
3. **The live worker sends no alerts yet.** `AlertGate` and `Dispatcher` are not constructed anywhere outside
   `alerting/`; the signal machine runs in the pass through the backtest runner. ([[REQ-INFRA-008]]'s Telegram
   link presupposes delivery that this feature does not add.)
4. **There is no code-commit source at run time.** `experiments/identity.py` takes the commit from `git` in a
   development checkout; the worker's container has no `.git`.
5. **Volume is large against the budget.** `CHANNELFLOW_TIMEFRAMES` is `5m,15m,30m,1h,4h,1d,1w` (≈460 final
   snapshots a day per series) over several series: on the order of two thousand snapshots a day. The deploy
   account holds 4.92 MON and a commit plus a resolve measured ≈0.0154 MON, so ≈0.0077 MON per transaction and
   ≈640 transactions in total. **One transaction per snapshot does not fit**, by roughly an order of magnitude a
   day; the requirement's own last acceptance line anticipates this.
6. **An input dataset is not the output table.** A snapshot written into `channel_snapshots` cannot name that
   table's own snapshot as its dataset version (it does not exist yet). The dataset version a record is
   reproducible from is the **input** it was computed from: the bars table's snapshot id and content hash.

### What "committed" means here

A record is *committed* when a reader holding the record and its context can verify it against a value written
by [[REQ-INFRA-006]]'s contract **without trusting this system**. That is satisfied either by committing the
record's hash directly or by committing a root over a batch whose membership the reader can check from a proof
this system publishes. The choice, and the batching window, belong to the plan, which must size them against
fact 5. What the spec fixes is the guarantee and what is measured.

### What a decision is

For this feature a **decision** is derived from the existing lifecycle, so that nothing new has to be invented
per bar: each `signal_transitions` row is one decision at a bar close (reached `CONFIRMED`, was `ALERTED`,
was `INVALIDATED` or `EXPIRED`, with its reason), and a candidate that reaches a terminal state without ever
having been `ALERTED` is a **NO ALERT** decision whose reason is that transition's reason. A suppression by the
freshness gate is likewise a decision, with its recorded reason. *Alternative considered and not chosen:* a
decision record for every series on every bar (which would be the volume in fact 5 many times over, and would
mostly say "nothing happened"). This is an assumption the user may reverse (see Assumptions).

### Why the hash binds four things

Principle XI: a result is reproducible from a dataset, a config, a code commit and (for models) an artifact
hash. The requirement fixes four inputs to the committed hash: **the record**, **the config hash**, **the input
dataset version**, **the code commit**. Change any one and the hash changes; that is the whole point, and it
means a record recomputed at a later commit or after a config change is a *different* record, never an edit
(Principle III).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A final channel snapshot is committed, and its hash can be recomputed (Priority: P1)

After a snapshot is final, its hash — bound to the config hash, the input dataset version and the code commit —
is committed.

**Why this priority**: The snapshot is the product's central artifact; without it the notary proves nothing
about the thing the product sells.

**Independent Test**: With a fake chain client, for one stored snapshot recompute the hash from the stored row,
the config hash, the dataset version and the commit, and compare with the value handed to the chain.

**Acceptance Scenarios**:

1. **Given** a final snapshot in `channel_snapshots`, **When** the notarizer processes it, **Then** exactly one
   hash for it is handed to the chain client, and recomputing it from the stored row plus the three context
   values gives the same value.
2. **Given** that snapshot, **When** any one of the four inputs is changed, **Then** the hash is different
   (four tests, one per input).
3. **Given** a snapshot whose bar is not final, or whose `source_max_event_time_ns` exceeds its `as_of_ns`,
   **When** the notarizer is offered it, **Then** it is refused and nothing is handed to the chain (Principle I).
4. **Given** a snapshot already notarized, **When** the pass runs again over the same data, **Then** nothing new
   is handed to the chain.

---

### User Story 2 - A decision, including NO ALERT, is committed the same way (Priority: P1)

Each decision is committed with the same four bindings; a decision not to alert is committed like an alert.

**Why this priority**: A notary that records only the winners is a highlight reel. The product's promise is
that it shows what it decided *including* silence.

**Independent Test**: Feed a candidate that ends `EXPIRED` without alerting and one that ends `ALERTED`;
both produce a committed hash by the same code path.

**Acceptance Scenarios**:

1. **Given** a candidate whose terminal transition is `INVALIDATED` or `EXPIRED` and which was never `ALERTED`,
   **When** it is processed, **Then** a NO ALERT decision carrying that transition's reason is committed.
2. **Given** a suppression recorded by the freshness gate, **When** it is processed, **Then** it is committed
   as a decision carrying the recorded reason.
3. **Given** the same decision processed in live and in replay, **When** both compute the hash with the same
   four inputs, **Then** the hashes are equal (Principle VII).

---

### User Story 3 - A chain outage never delays a signal, and nothing is lost (Priority: P1)

The write is asynchronous. When the chain is unreachable signals are still produced and stored; unsent commits
wait in a visible outbox and drain, in order and without duplicates, when the chain returns.

**Why this priority**: [[REQ-WP-008]]'s rule — never block the engine on delivery — applies. A notary that can
stall the radar is worse than none.

**Independent Test**: A fake chain client that fails; run passes; observe signals stored, outbox non-empty and
visible; make the chain work; observe the outbox drain exactly once per item.

**Acceptance Scenarios**:

1. **Given** the chain is unreachable, **When** a pass runs, **Then** snapshots, signals and transitions are
   written exactly as without the notary and the pass takes no longer than the bound in SC-003.
2. **Given** unsent commits, **When** an operator looks, **Then** the count, the age of the oldest and the last
   error are visible (a metric and a listing).
3. **Given** the chain returns, **When** the outbox drains, **Then** every item is sent once; an item whose hash
   the chain reports as already committed is checked against the stored commit and treated as done, not retried
   forever (the contract rejects a duplicate; a crash between sending and recording must not wedge the queue).

---

### User Story 4 - Anyone can check a record against the chain (Priority: P2)

Given a stored record and its context, a command recomputes the hash and says whether the chain has it, in which
block, and how long after the bar closed.

**Why this priority**: The promise is "checkable by anyone". Without a checking path the commits are decoration.

**Independent Test**: Commit through a fake chain, then verify the record; tamper with one field; verification
fails and names that the hash is not on the chain.

**Acceptance Scenarios**:

1. **Given** a notarized record, **When** it is verified, **Then** the result reports committed, the block time,
   the transaction and the interval from the record's bar close.
2. **Given** the same record with any field altered, **When** verified, **Then** the result is "not committed".
3. **Given** a record that is not yet committed (in the outbox), **When** verified, **Then** the result says
   pending, never "committed".

---

### User Story 5 - The claim the product may make is the measured one (Priority: P2)

The interval from bar close to the commit's block time is measured on testnet and recorded, and the product's
wording is that figure.

**Why this priority**: [[REQ-INFRA-006]]: a block time proves *no later than*, not *before the move*. The honest
claim is "committed within N seconds of bar close", with N measured.

**Independent Test**: The measurement report exists with sample size, window and percentiles; the wording
quotes it; a test fails if the repository's user-facing text claims "before the move".

**Acceptance Scenarios**:

1. **Given** a measurement run on testnet, **When** it ends, **Then** the outcome note records the number of
   commits, the series covered, the duration, and median / p95 / max of (block time − bar close time).
2. **Given** the product's user-facing text about notarization, **When** it is searched, **Then** it states the
   measured figure and contains no claim that a commit precedes a price move.

### Edge Cases

- **Code commit absent or tree dirty** (fact 4): the record is not committed under the normal kind. It is stored
  as *unnotarizable* with the reason (ADR-037: a component is present or explicitly absent, never merely
  missing), and the outbox shows it. A blank commit is never hashed in.
- **Late or corrected data** (a bar arrives after a pass, a config changes): the new record has a different
  dataset version or config hash and therefore a different hash; the old commit stands (Principle III). Nothing
  is "updated".
- **Same record, different pass interval or restart**: the hash depends on the record and its four inputs, never
  on when the pass ran, so a restart produces the same hash and no second commit.
- **A crash between sending and recording**: on restart the item is still in the outbox; the chain's own
  `commitOf` decides whether it is already done.
- **Balance exhausted** (fact 5): commits stop being affordable; the outbox grows, the condition is visible and
  alarms, and signals are unaffected. The system never spends from an account it was not given.
- **`barTs` units**: the contract takes seconds; records carry nanoseconds. A bar close that is not a whole
  second is a defect, not rounded silently.
- **A reorganisation or a dropped transaction**: a commit counts as done only after its receipt succeeds and the
  hash reads back with `commitOf`; a missing receipt is "still pending".
- **Clock**: the "interval from bar close" uses the chain's block time and the bar's close time; the local
  clock is never involved.
- **Key exposure**: the live worker now needs signing authority. The key is a mounted keystore and password
  file, never an environment value, an image layer or a compose literal ([[REQ-INFRA-006]]'s rule, extended to a
  long-running process).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After a record becomes final, the system MUST compute its committed hash from exactly four
  inputs: the record in its canonical encoding, the config hash, the input dataset version, and the code commit.
- **FR-002**: The canonical encoding MUST be the repository's existing one — the lakehouse row encoding
  ([[ADR-053]]) for the record, `config_hash` and `dataset_reference` (`experiments/hashing.py`) for the
  context. No second definition of what a record is MAY be introduced.
- **FR-001a**: The hashed bytes MUST begin with a record kind and a hash-scheme version, so that a change of
  scheme (a fifth input, a different digest) can never produce a value that collides with an older one.
- **FR-003**: The hash MUST change when any one of the four inputs changes, and MUST NOT depend on when or in
  which process it was computed.
- **FR-004**: Final channel snapshots MUST be notarized. A snapshot that is not final, or whose source data time
  exceeds its `as_of`, MUST be refused (Principle I).
- **FR-005**: Decisions MUST be notarized: each `signal_transitions` row, each NO ALERT outcome derived from a
  terminal transition of a never-alerted candidate (with its reason), and each freshness-gate suppression (with
  its reason). A decision not to alert MUST go through the same path as an alert.
- **FR-006**: A record MUST be committed at most once; processing the same record again MUST send nothing.
- **FR-007**: The write MUST be asynchronous and MUST NOT block or slow record production beyond the bound in
  SC-003. A chain outage MUST delay notarization only.
- **FR-008**: Unsent commits MUST sit in a durable outbox that is visible (count, oldest age, last error), that
  survives a restart, and that drains without duplicates when the chain returns.
- **FR-009**: A commit MUST count as done only after the transaction's receipt succeeded and the committed value
  reads back from the contract; a hash the contract reports as already committed MUST be reconciled against the
  stored commit rather than retried indefinitely.
- **FR-010**: If the code commit, config hash or input dataset version is absent, or the working tree is dirty,
  the record MUST NOT be committed; it MUST be stored as unnotarizable with the reason and shown in the outbox.
- **FR-011**: Time MUST be explicit (Principle II): the committed bar time is the record's `bar_close_time`
  converted to whole seconds; the latency figure is `block_time − bar_close_time`; no field is derived from
  `ingest_time` or a local clock.
- **FR-012**: The design MUST be sized before it is chosen: series × timeframes × records a day, against the
  fee and the rate limit of the testnet, and the per-record cost; the sizing and its conclusion MUST be written
  down in the plan, and the commit granularity (one per record, or a batch with proofs) MUST follow from it.
- **FR-013**: A reader holding a record and its context MUST be able to verify it against the chain without
  trusting this system; a verification command MUST report committed / pending / not committed, the block, the
  transaction and the interval from bar close.
- **FR-014**: The interval from bar close to the commit's block time MUST be measured on testnet and recorded
  (sample size, series, duration, median, p95, max), and any user-facing statement MUST quote that figure.
  No user-facing text MAY claim a commit precedes a price move.
- **FR-015**: Signing authority for the running process MUST come from a mounted keystore and password file;
  the key MUST NOT appear in an environment variable's value, an image, a compose file or a log.
- **FR-016**: Thresholds and endpoints (RPC URL, chain id, contract address, batch window, outbox limits,
  confirmation requirement) MUST be configuration (Principle X).
- **FR-017**: Live and replay MUST share one hashing code path (Principle VII): the same record and the same
  four inputs give the same hash in both.
- **FR-018**: Every file added carries a requirement trace (Principle XIV).

### Key Entities

- **Notarized record**: a final snapshot or a decision, its kind, its canonical bytes, and the four inputs.
- **Record hash**: the repository's digest (SHA-256, as `experiments/hashing.py`) over the length-prefixed,
  type-tagged encoding of scheme version + kind + record + config hash + dataset version + code commit.
- **Outbox entry**: record hash, kind, bar close time, state (`pending`, `sent`, `confirmed`, `unnotarizable`),
  attempts, last error, and — once confirmed — transaction hash, block number, block time.
- **Commit evidence**: what [[REQ-INFRA-006]]'s contract holds for a hash (`barTs`, `blockTime`, `committer`),
  plus, if batched, the root and the inclusion proof.
- **Latency measurement**: sample, series, window, median / p95 / max of block time − bar close time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For one stored snapshot and one stored decision, recomputing the hash from the stored record plus
  the config hash, dataset version and commit gives the value handed to the chain; changing each of the four
  inputs, one at a time, changes it (eight tests).
- **SC-002**: A NO ALERT decision and an alert are committed by the same code, shown by one test that feeds
  both and asserts the same path.
- **SC-003**: With the chain made unreachable, a pass over the fixture series completes in no more than the
  same pass without the notary plus a bound stated in the plan; signals are produced and stored identically.
- **SC-004**: With the chain restored, every outbox entry is sent exactly once, in order, and a simulated crash
  between sending and recording produces no duplicate and no wedged entry.
- **SC-005**: The plan contains the volume sizing (FR-012) with numbers and a conclusion, and the measured
  per-transaction cost from [[REQ-INFRA-006]] is the figure used.
- **SC-006**: On testnet, at least 50 records across at least 3 series over at least one hour are committed,
  verified with the verification command, and their bar-close-to-block latency is recorded as median, p95 and
  max in the outcome note.
- **SC-007**: A test fails if user-facing text claims a commit precedes a price move, or quotes a latency
  figure other than the recorded one.
- **SC-008**: The working tree and git history contain the signing key zero times; the live worker starts from
  a mounted keystore.

## Assumptions

- **Decision granularity (reversible):** a decision is a lifecycle transition, a never-alerted terminal
  outcome, or a gate suppression — not a per-bar "nothing happened" record. This keeps volume proportional to
  events. If the owner wants a decision for every series on every bar, FR-005 and the sizing change; that is a
  separate, larger commitment.
- **"After a bar closes" is "once final in the lakehouse"** (fact 1). A faster, event-driven notarization is a
  different feature; the measured latency includes the pass interval and says so.
- **The input dataset version is the bars table snapshot** (id and content hash) the record was computed from
  (fact 6), obtained from the lakehouse at compute time.
- **The code commit is injected at build** as configuration (fact 4); a build without it yields only
  unnotarizable records, visibly, rather than blank commits.
- **The config hash** is `config_hash` over the settings that affect the record (the plan enumerates them).
- The deploy account's faucet balance (4.92 MON, ≈0.0077 MON per transaction) is the budget; topping it up is a
  human action and never automated.
- Delivery of alerts to Telegram is not part of this feature ([[REQ-INFRA-008]]), and the worker does not
  deliver any today (fact 3).
- **The model artifact hash is not an input.** The requirement fixes four inputs. The baseline channel fits no
  trained model, so there is no artifact to bind; if a model is ever introduced its artifact hash joins the
  inputs under a new hash-scheme version (FR-001), never silently.
