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

## R8. What is "the config" a snapshot depends on?

`BacktestRunner` is composed of `RollingOLSChannel` (a frozen dataclass: model name/version, lookback, …) and
`SignalMachine` (a dataclass holding its detector and thresholds), plus the gap threshold setting
(`CHANNELFLOW_GAP_THRESHOLD`) and the timeframe. The config hash is taken over the components' own declared
fields (recursively, via `dataclasses.fields`), the class names, and the settings that influence the pass, so
adding a parameter to a component changes the hash without anyone remembering to list it. The first task
enumerates the fields as they are today and fails loudly on a value `config_hash` cannot encode
(`UnhashableConfig`) rather than skipping it.

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
