# Research: Notarize every final channel snapshot and decision

Resolved before design. Date 2026-10-08. "Measured" means read or run on the running system today.

## R1. How large is the problem?

Measured read-only in the `worker` container (`channel_snapshots`, `signal_transitions`, `bars`): 28,187
snapshots over 21 days, 2,298–2,302 on each of the last three full days, from 5 series × 5 timeframes
(5m 15m 30m 1h 4h; `1d` and `1w` are configured and produce none yet). Transitions: 2,074 over 21 days, median
92 a day (by target state: approach 1,055, invalidated 539, touch 263, expired 95, rejection_pending 71,
confirmed 51, **alerted 0**). The sizing table is in `plan.md`; the conclusion is that a root per 30 minutes
fits the faucet balance for ≈ 12.5 days and a transaction per record for ≈ 6 hours.

## R2. Where do decisions come from?

`signal_transitions` is not a reliable source. 422 signals are non-terminal; **341 are older than 24 hours**,
3 older than 7 days, oldest 374 hours. Of the 341, 294 are still `approach` with one transition. Cause, in
`pipeline/replay.py`: `SignalRecorder.__call__` skips any candidate with `opened_at_ns <= after_ns` where
`after_ns` is the latest `opened_at_ns` already in the core table, and `flush` writes each remaining candidate
once. So a candidate is written the first time the pass sees it, with the history it has then, and never
again. Consequence for this feature: terminal outcomes (the NO ALERTs) of already-recorded candidates are not
in the table. Consequence for the product: the signals table shows stale states. The pass replays the whole bar
history every time, so a subscriber on the bus sees every transition as it re-happens; that is the source.

## R3. How does the pass read its input?

`run_pass` calls `bars_table.read_bars(table)` once for the flow features and each `run_series` calls
`read_bars(table, venue=…, symbol=…, timeframe_ns=…)` again; neither passes `snapshot_id`, so each reads
whatever is current at that moment. The bars table has 14,020 snapshots (a commit every few seconds), so the
dataset a snapshot "was computed from" is not recorded anywhere. `read_bars` already accepts `snapshot_id`;
pinning once per pass is a small, local change.

## R4. What does a commit cost, and what does Monad charge for?

The smoke `commit` (`0x32a6…9785`): gas used 79,491, gas limit 79,491 (what `cast` set), effective gas price
103 gwei, ≈ 0.0082 MON; the balance difference over the smoke pair was 0.0154 MON (≈ 0.0077 each). Gas
estimate for a fresh `commit` of a new hash: 79,455. Monad documents that the **gas limit**, not gas used, is
what is charged; the receipt above has limit = used so it cannot confirm that. The first chain task sends one
commit with a deliberately larger limit and compares the balance difference, so the margin the service adds is
a measured cost.

## R5. Finality and block time on Monad testnet

Measured: `eth_getBlockByNumber` accepts `latest`, `safe` and `finalized`; at one reading latest = 69,267,720,
safe = …719, finalized = …718. Ten blocks spanned 3 seconds (≈ 0.3–0.4 s per block). So `finalized` is ≈ 2
blocks, under a second, behind the head; waiting for it costs almost nothing and removes the reorg question.

## R6. What exists on the chain side of this repository?

`src/channelflow/chain/` is read-side only: `ChainDataProvider` (`get_block`, `get_logs`, `eth_call`),
`ProviderPool`, `FinalityPolicy`, decoders for HyperEVM. It has no signer, no `eth_sendRawTransaction`, no
nonce handling, and no profile for Monad. `httpx` and `eth-hash[pycryptodome]` (Keccak) are dependencies;
`eth-account` is not. The notary needs nine JSON-RPC calls (`eth_chainId`, `eth_getBalance`,
`eth_getTransactionCount`, `eth_gasPrice`, `eth_estimateGas`, `eth_sendRawTransaction`,
`eth_getTransactionReceipt`, `eth_call`, `eth_getLogs`/`eth_getBlockByNumber`) and one signature; a dedicated
small client is less than the surface of `web3.py` and is testable with a fake transport. The keystore Foundry
wrote (`~/.foundry/keystores/notary-deployer`) is a standard Web3 Secret Storage v3 file, which
`eth_account.Account.decrypt` opens.

## R7. Which digest, which tree?

Nothing on-chain checks the committed value, so the digest is free. SHA-256 is already the repository's
(`experiments/hashing.py`), is in every language's standard library, and keeps the records, the tree and the
verification in one family. The tree is RFC 6962 (Certificate Transparency) generalised in RFC 9162: domain-
separated leaf and node prefixes, no duplication of the last node, and a published inclusion-proof algorithm.
Tested against the RFC's published tree shapes (sizes 1–8) in the tasks.

## R8. What is "the config" a snapshot depends on? (inventory done in T004, 2026-10-08)

The pass runs `BacktestRunner()` with its defaults. Read from the live objects:

* `RollingOLSChannel` (frozen dataclass; **all configuration**): `lookback=60`, `quantile_low=0.1`,
  `quantile_high=0.9`, `weights=None`, `bands='residual_quantiles'`, `band_sigmas=1.2816`.
* `SignalMachine` (mutable dataclass; **configuration and state mixed**). Configuration: `zone_upper`,
  `zone_lower`, `zone_middle`, `overshoot_tolerance`, `min_quality`, `slope_threshold`, `expiry_bars`, `opens`,
  and `detector`. **State, which must never enter a hash:** `candidate` and `_awaiting_zone_exit` (they change on
  every bar; a hash that included them would differ for every record and mean nothing).
* `detector` is a plain class, not a dataclass (`CloseBackInside(min_distance_pct_of_width=0.15)`): it is
  configuration through its `name` and its public attributes.
* `CHANNELFLOW_GAP_THRESHOLD` (`Settings.gap_threshold`, default 1). The channel's own
  `_find_gap_boundary` passes the literal `threshold=1` to `is_gap` rather than reading the setting, so changing the
  setting does not change the channel window today; it is included anyway because it is the configured value, and
  the discrepancy is noted for the owner of REQ-WP-087.
* The extremum detector (`DirectionalChangeDetector`) is out of scope: extrema are not notarized here.

**Consequence for the design.** Walking `dataclasses.fields` recursively (what the plan first said) would include
the machine's state. The config hash is taken over an **explicit list of configuration fields per component**,
and a completeness test enumerates every field of every component and fails unless it is classified as
configuration or as state/observer. A parameter added tomorrow without being classified fails the suite; it does
not silently stay out of the hash. A value `config_hash` cannot encode (`UnhashableConfig`) makes the pass's
records unnotarizable with that reason; it is never skipped.

## R9. Code commit at run time

Containers have no `.git`. `experiments/identity.py` already models "a commit, and whether the tree was dirty"
(`CodeVersion`), with the rule that a commit from a dirty tree names a tree that exists nowhere. The image build
takes `CHANNELFLOW_CODE_COMMIT` (40 hex) and `CHANNELFLOW_CODE_DIRTY`; the notary reads them through
`CodeVersion` and its rule is applied as it stands.

## R10. Compose secrets and the unprivileged user

Images run as uid 10001. File-based compose secrets keep the host file's owner and mode in a non-swarm stack,
so a 600 root-owned keystore is unreadable by that user. The deploy places read-only copies in a directory owned
by uid 10001 with mode 400, outside the repository; the compose file names them by variable, never by literal.
The service logs the signing *address* and refuses to start when it is not the contract's `owner()`.

## R11. What the dataset reference looks like

`dataset_reference({"bars": (snapshot_id, content_hash)})` gives one string over the pinned bars snapshot. The
`bars` table was chosen because every record in this feature is computed from bars alone; if a later record also
reads flow features or quotes, their snapshots join the mapping and the scheme version moves.

## R4 — finding (T002, 2026-10-08): Monad charges the gas limit

One real `commit` of a throw-away hash sent with a deliberately raised limit: estimate **79,455**, limit
**111,237** (+40 %), price 103 gwei. The receipt reports `gasUsed = 111,237` — the limit, not what the call
needed — and the balance fell by exactly `111,237 × price` (0.011457 MON; the ratio of the balance difference to
`limit × price` is 1.0000). So on this chain **the limit is the price**: every unit of margin is paid. The
service sets the limit to the estimate times a small configured margin (default 1.05, ≈ +0.0004 MON a commit),
and a transaction that runs out of gas still costs its whole limit, so the margin is a trade between a
redundant 5 % and a failed commit that costs 100 % and must be repeated. Earlier receipts could not show this
because `cast` had set limit = estimate.

## R12. How often does a record actually reach the lakehouse? (T001, 2026-10-08)

Read from `docker logs -t` of the worker over three hours. A cycle is: the flow step (`flow rows written`), then
every `(series, timeframe)` — 5 series × 7 timeframes, 20–50 s each, `1w` skipped for lack of bars — then `next
pass in 300s`. Measured: the channel part of a pass takes **1,012–1,290 s (17–21 min)**; the flow step before it
takes about **10–14 min**; plus the 5-minute sleep, so one **start-to-start cycle is 28–35 min**. The cost is
dominated by work that repeats every cycle regardless of what is new: each series replays its whole bar history
and `watermark()` reads whole tables.

Consequences for this feature:

1. Records arrive in clumps, once per cycle. A 5-minute snapshot is in the lakehouse up to ~35 minutes after its
   bar closed — before the notary adds anything. The claim the product can make is therefore minutes-to-an-hour,
   and the measured figure will say so.
2. A batch window much shorter than the cycle cannot reduce latency (nothing new arrives between clumps); 30
   minutes is roughly one cycle, so about one root per cycle (≈ 45 a day, inside the 48 estimated).
3. The registrar must not add a full read to a pass that is already dominated by full reads: the tracker's
   registered-identity set is read once per pass, and snapshots are registered from the recorder's own buffer.
4. A pass-time bound cannot be a comparison with "last week": durations moved 1,012 → 1,290 s within five passes
   and the cause (history growing, and my own read-only measurements running in the same container) is not
   separable from here. The bound is therefore two-part (plan): a deterministic A/B on a fixture, and on the live
   stack 110 % of the *longest* of the five most recent passes before the change.
