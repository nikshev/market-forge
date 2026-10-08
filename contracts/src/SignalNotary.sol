// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

// @trace: REQ-INFRA-006

/// @title SignalNotary
/// @notice A write-once notary of this system's own decisions: it records that a hash was committed, and
///         later what became of it. It is not a public registry -- one account writes.
/// @dev What a commit proves is that the hash existed no later than the block that recorded it. It does
///      not prove the decision preceded a price move. The two times it keeps are therefore separate and
///      never derived from one another (Principle II):
///        - `barTs`      the bar's close time, in seconds, **as claimed by the committer**;
///        - `blockTime`  `block.timestamp`, in seconds, assigned by the chain.
///      The contract does not validate `barTs`: it has no trusted clock for it, and a check it cannot
///      make would only look like one.
///
///      There is no function that deletes or overwrites a commit or an outcome, no ownership transfer
///      and no upgrade path, and the contract has no `receive`, no `fallback` and no payable function,
///      so it can hold no funds. A leaked owner key is remedied by a new contract, not a rotation.
contract SignalNotary {
    struct Commit {
        uint64 barTs; // bar_close_time, seconds, committer-supplied
        uint64 blockTime; // block_time, seconds, chain-assigned
        address committer; // never zero for a stored commit, so it doubles as the "exists" flag
    }

    /// @dev Accepted outcomes are the contiguous range 1..3: 1 target hit, 2 invalidated, 3 expired.
    uint8 internal constant TARGET_HIT = 1;
    uint8 internal constant EXPIRED = 3;

    /// @notice The one account allowed to write. Stored (not `immutable`) so the deployed runtime
    ///         bytecode equals the compiler's output exactly and can be compared byte for byte.
    address public owner;

    event Committed(bytes32 indexed hash, uint64 barTs, address committer);
    event Resolved(bytes32 indexed hash, uint8 outcome);

    error NotOwner();
    error ZeroOwner();
    error ZeroHash();
    error AlreadyCommitted();
    error NotCommitted();
    error AlreadyResolved();
    error BadOutcome();

    mapping(bytes32 => Commit) private commits;
    mapping(bytes32 => uint8) private outcomes; // 0 = unresolved

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address owner_) {
        if (owner_ == address(0)) revert ZeroOwner();
        owner = owner_;
    }

    /// @notice Record that `hash` was committed for the bar that closed at `barTs`.
    function commit(bytes32 hash, uint64 barTs) external onlyOwner {
        if (hash == bytes32(0)) revert ZeroHash();
        if (commits[hash].committer != address(0)) revert AlreadyCommitted();

        commits[hash] = Commit({barTs: barTs, blockTime: uint64(block.timestamp), committer: msg.sender});
        emit Committed(hash, barTs, msg.sender);
    }

    /// @notice Record what became of a committed hash: 1 target hit, 2 invalidated, 3 expired.
    function resolve(bytes32 hash, uint8 outcome) external onlyOwner {
        if (commits[hash].committer == address(0)) revert NotCommitted();
        if (outcomes[hash] != 0) revert AlreadyResolved();
        if (outcome < TARGET_HIT || outcome > EXPIRED) revert BadOutcome();

        outcomes[hash] = outcome;
        emit Resolved(hash, outcome);
    }

    /// @notice The commit recorded for `hash`; all zeros if there is none.
    function commitOf(bytes32 hash) external view returns (uint64 barTs, uint64 blockTime, address committer) {
        Commit storage c = commits[hash];
        return (c.barTs, c.blockTime, c.committer);
    }

    /// @notice The outcome recorded for `hash`; 0 while unresolved.
    function outcomeOf(bytes32 hash) external view returns (uint8 outcome) {
        return outcomes[hash];
    }
}
