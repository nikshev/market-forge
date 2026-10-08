# Third-party verification: encoding, tree and bundle

Everything a reader needs to check a record against the chain without our code. Scheme version **1**.

## 1. The record hash

```
record_hash = SHA-256(
    "CFN" ‖ uint8(scheme_version)
    ‖ frame(kind) ‖ frame(record_bytes) ‖ frame(config_hash)
    ‖ frame(dataset_ref) ‖ frame(code_commit)
)
frame(x) = uint32_be(len(x)) ‖ x            # x is UTF-8 text, or raw bytes for record_bytes
```

* `kind`: `snapshot`, `decision` or `suppression`.
* `record_bytes`: the lakehouse row encoding ([[ADR-053]]) of the record under its schema — for a snapshot the
  `channel_snapshots` schema (`src/channelflow/tables/channels.py`), for a decision `DECISION_SCHEMA`
  (`data-model.md`). The bundle carries these bytes, so a reader hashes them as given and need not re-encode.
* `config_hash`, `dataset_ref`: the strings produced by `experiments/hashing.py` (`config_hash`,
  `dataset_reference`); the bundle carries them.
* `code_commit`: the 40-hex commit the image was built from.

Changing any of the four inputs changes `record_hash`; this is intended.

## 2. The tree (RFC 9162 §2.1, SHA-256)

```
leaf(h)    = SHA-256( 0x00 ‖ h )            h = the 32-byte record_hash
node(l, r) = SHA-256( 0x01 ‖ l ‖ r )
MTH(D[n])  = leaf(D[0])                      if n == 1
           = node(MTH(D[0:k]), MTH(D[k:n]))  k = the largest power of two strictly less than n
```

Leaves are ordered by `(bar_close_time_ns, kind, record_id)`. The root is committed on-chain as the `hash`
argument of `SignalNotary.commit(hash, barTs)`, with `barTs` = the largest leaf bar-close time in whole seconds.
Inclusion proofs are verified with the algorithm of RFC 9162 §2.1.3.2.

## 3. The bundle (JSON)

```json
{
  "scheme_version": 1,
  "record": { "record_id": "...", "kind": "snapshot", "record_bytes": "<hex>" },
  "context": { "config_hash": "...", "dataset_ref": "...", "code_commit": "<40 hex>" },
  "record_hash": "<64 hex>",
  "inclusion": { "leaf_index": 17, "tree_size": 53, "path": ["<64 hex>", "..."] },
  "root": "<64 hex>",
  "chain": { "chain_id": 10143, "contract": "0x4a09…6682", "rpc_hint": "https://testnet-rpc.monad.xyz" },
  "commit": { "tx_hash": "0x…", "block_number": 0, "block_time": 0 }
}
```

`commit` is a claim to check, not evidence: the verifier asks the chain.

## 4. The check

1. Recompute `record_hash` from `record_bytes` and `context`; it must equal `record_hash`.
2. Verify the inclusion proof of `leaf(record_hash)` against `root`.
3. Call `commitOf(root)` on the contract at `chain.contract` (selector for `commitOf(bytes32)`): it returns
   `(barTs, blockTime, committer)`. A non-zero `committer` means the root was committed; `blockTime` is the
   chain's.
4. Report: committed / not committed; `blockTime`; and `blockTime − bar_close_time` for the record, where
   `bar_close_time` is read from the record's own bytes. A passing check proves the record existed **no later
   than `blockTime`**. It does not prove the record preceded any price move.
