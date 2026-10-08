# Data model: SignalNotary

Contract state, in the contract's own terms. Time meaning is stated per field (Principle II).

## Storage

| Name | Type | Meaning |
|---|---|---|
| `owner` | `address` (public) | The one account allowed to write. Set in the constructor; never zero; never changed. |
| `commits` | `mapping(bytes32 => Commit)` | A record exists iff `committer != address(0)`. |
| `outcomes` | `mapping(bytes32 => uint8)` | `0` = unresolved; `1` target hit, `2` invalidated, `3` expired. |

### `Commit`

| Field | Type | Time meaning |
|---|---|---|
| `barTs` | `uint64` | `bar_close_time` in **seconds**, supplied by the committer. Not validated: the contract has no trusted clock for it. |
| `blockTime` | `uint64` | `block_time` in **seconds**: `block.timestamp` of the committing block. Assigned by the chain. |
| `committer` | `address` | Always `owner` (only the owner can call); stored so the record is self-describing and the "exists" test needs no extra flag. |

`barTs` and `blockTime` are never derived from one another.

## Events

- `Committed(bytes32 indexed hash, uint64 barTs, address committer)`
- `Resolved(bytes32 indexed hash, uint8 outcome)`

## Off-chain record: `deployments/monad-testnet.json`

Written by `tools/notary/deploy.py` only after read-back; absent before.

| Field | Meaning |
|---|---|
| `chain_id` | `10143` |
| `address` | Created contract address, as returned by the receipt |
| `tx_hash` | Deployment transaction |
| `block_number` | Block of the receipt |
| `block_time` | Seconds, from the block header (chain-assigned) |
| `owner` | `owner()` read from the contract |
| `deployer` | Sender of the deployment transaction |
| `source_commit` | `git rev-parse HEAD` at deploy, with `contracts/` clean |
| `solc` | Compiler version used |
| `deployed_code_hash` | keccak256 of the runtime bytecode read from the chain |
| `smoke` | `{ "hash", "commit_tx", "resolve_tx", "outcome" }`, filled by `smoke.py` after it reads both back |

`.env.example` carries `MONAD_NOTARY_ADDRESS` with the same address, documented, and the other `MONAD_*`
variables (`MONAD_RPC_URL`, `MONAD_CHAIN_ID`, `MONAD_EXPLORER_URL`) with their meaning and defaults.
