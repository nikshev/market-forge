# Contract interface: SignalNotary

```solidity
constructor(address owner_);                                   // reverts ZeroOwner if owner_ == address(0)

function commit(bytes32 hash, uint64 barTs) external;          // onlyOwner
function resolve(bytes32 hash, uint8 outcome) external;        // onlyOwner

function owner() external view returns (address);
function commitOf(bytes32 hash) external view returns (uint64 barTs, uint64 blockTime, address committer);
function outcomeOf(bytes32 hash) external view returns (uint8 outcome);   // 0 = unresolved

event Committed(bytes32 indexed hash, uint64 barTs, address committer);
event Resolved(bytes32 indexed hash, uint8 outcome);

error NotOwner();  error ZeroOwner();  error ZeroHash();
error AlreadyCommitted();  error NotCommitted();
error AlreadyResolved();   error BadOutcome();
```

No `receive`, no `fallback`, no payable function: value sent to the contract reverts (FR-008).
No function deletes or overwrites a stored value (FR-005).

## Required forge tests (the names the pytest driver lists)

| Test | Proves |
|---|---|
| `test_commit_emits_and_records` | FR-001, FR-007: event fields; `commitOf` returns `barTs`, block time and committer, as two separate values |
| `test_commit_twice_reverts_and_keeps_first` | FR-002, FR-005: duplicate reverts; first `barTs` unchanged |
| `test_commit_zero_hash_reverts` | FR-002 |
| `test_resolve_emits_and_records` | FR-003 for each of 1, 2, 3 |
| `test_resolve_uncommitted_reverts` | FR-004 |
| `test_resolve_twice_reverts_and_keeps_first` | FR-004, FR-005 |
| `test_resolve_outcome_out_of_range_reverts` | FR-004: 0, 4, 255; hash stays resolvable afterwards |
| `test_non_owner_cannot_commit` | FR-006 |
| `test_non_owner_cannot_resolve` | FR-006 |
| `test_constructor_rejects_zero_owner` | FR-006 |
| `test_owner_is_the_constructor_argument` | FR-007 / FR-006: `owner()` returns the constructor argument |
| `test_value_is_rejected` | FR-008: call with value and plain transfer both revert |
| `test_block_time_is_not_bar_time` | FR-007 / Principle II: warp the chain, commit an old `barTs`; the two fields differ and each is what was set |
