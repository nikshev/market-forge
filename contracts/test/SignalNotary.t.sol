// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

// @trace: REQ-INFRA-006
// The offline suite for SignalNotary. One test per behaviour in specs/142-signal-notary-contract/spec.md
// FR-001..FR-008; tests/contracts/test_signal_notary_suite.py lists these names and fails if one is
// missing, renamed or red.

import {SignalNotary} from "../src/SignalNotary.sol";
import {Vm} from "./utils/Vm.sol";

contract SignalNotaryTest {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    SignalNotary internal notary;
    address internal constant STRANGER = address(0xBAD);
    bytes32 internal constant H = keccak256("decision-1");
    bytes32 internal constant COMMITTED_SIG = keccak256("Committed(bytes32,uint64,address)");
    bytes32 internal constant RESOLVED_SIG = keccak256("Resolved(bytes32,uint8)");

    function setUp() public {
        notary = new SignalNotary(address(this));
    }

    // Accepting value would be a way for the contract to hold funds (FR-008); it must not.
    // (No receive/fallback is declared, so this contract being payable is irrelevant to the notary.)
    receive() external payable {}

    // ---- helpers ----------------------------------------------------------------------------------

    function _commitOf(bytes32 h) internal view returns (uint64 barTs, uint64 blockTime, address committer) {
        return notary.commitOf(h);
    }

    // ---- FR-001, FR-007 ---------------------------------------------------------------------------

    function test_commit_emits_and_records() public {
        vm.warp(1_000);
        vm.recordLogs();
        notary.commit(H, 940);

        Vm.Log[] memory logs = vm.getRecordedLogs();
        assert(logs.length == 1);
        assert(logs[0].emitter == address(notary));
        assert(logs[0].topics[0] == COMMITTED_SIG);
        assert(logs[0].topics[1] == H);
        (uint64 barTs, address committer) = abi.decode(logs[0].data, (uint64, address));
        assert(barTs == 940);
        assert(committer == address(this));

        (uint64 storedBarTs, uint64 blockTime, address storedCommitter) = _commitOf(H);
        assert(storedBarTs == 940);
        assert(blockTime == 1_000);
        assert(storedCommitter == address(this));
    }

    // ---- FR-002, FR-005 ---------------------------------------------------------------------------

    function test_commit_twice_reverts_and_keeps_first() public {
        vm.warp(1_000);
        notary.commit(H, 940);

        vm.warp(2_000);
        vm.expectRevert(SignalNotary.AlreadyCommitted.selector);
        notary.commit(H, 1_900);

        (uint64 barTs, uint64 blockTime,) = _commitOf(H);
        assert(barTs == 940);
        assert(blockTime == 1_000);
    }

    function test_commit_zero_hash_reverts() public {
        vm.expectRevert(SignalNotary.ZeroHash.selector);
        notary.commit(bytes32(0), 940);
    }

    // ---- FR-003 -----------------------------------------------------------------------------------

    function test_resolve_emits_and_records() public {
        for (uint8 outcome = 1; outcome <= 3; outcome++) {
            bytes32 h = keccak256(abi.encode("decision", outcome));
            notary.commit(h, 940);

            vm.recordLogs();
            notary.resolve(h, outcome);

            Vm.Log[] memory logs = vm.getRecordedLogs();
            assert(logs.length == 1);
            assert(logs[0].emitter == address(notary));
            assert(logs[0].topics[0] == RESOLVED_SIG);
            assert(logs[0].topics[1] == h);
            assert(abi.decode(logs[0].data, (uint8)) == outcome);
            assert(notary.outcomeOf(h) == outcome);
        }
    }

    // ---- FR-004 -----------------------------------------------------------------------------------

    function test_resolve_uncommitted_reverts() public {
        vm.expectRevert(SignalNotary.NotCommitted.selector);
        notary.resolve(H, 1);
        assert(notary.outcomeOf(H) == 0);
    }

    function test_resolve_twice_reverts_and_keeps_first() public {
        notary.commit(H, 940);
        notary.resolve(H, 1);

        vm.expectRevert(SignalNotary.AlreadyResolved.selector);
        notary.resolve(H, 2);
        assert(notary.outcomeOf(H) == 1);

        vm.expectRevert(SignalNotary.AlreadyResolved.selector);
        notary.resolve(H, 1);
        assert(notary.outcomeOf(H) == 1);
    }

    function test_resolve_outcome_out_of_range_reverts() public {
        notary.commit(H, 940);

        uint8[3] memory bad = [uint8(0), uint8(4), uint8(255)];
        for (uint256 i = 0; i < bad.length; i++) {
            vm.expectRevert(SignalNotary.BadOutcome.selector);
            notary.resolve(H, bad[i]);
        }

        // A rejected outcome leaves the hash resolvable.
        assert(notary.outcomeOf(H) == 0);
        notary.resolve(H, 3);
        assert(notary.outcomeOf(H) == 3);
    }

    // ---- FR-006 -----------------------------------------------------------------------------------

    function test_non_owner_cannot_commit() public {
        vm.prank(STRANGER);
        vm.expectRevert(SignalNotary.NotOwner.selector);
        notary.commit(H, 940);

        (,, address committer) = _commitOf(H);
        assert(committer == address(0));
    }

    function test_non_owner_cannot_resolve() public {
        notary.commit(H, 940);

        vm.prank(STRANGER);
        vm.expectRevert(SignalNotary.NotOwner.selector);
        notary.resolve(H, 1);
        assert(notary.outcomeOf(H) == 0);
    }

    function test_constructor_rejects_zero_owner() public {
        vm.expectRevert(SignalNotary.ZeroOwner.selector);
        new SignalNotary(address(0));
    }

    function test_owner_is_the_constructor_argument() public {
        SignalNotary other = new SignalNotary(STRANGER);
        assert(other.owner() == STRANGER);
        assert(notary.owner() == address(this));
    }

    // ---- FR-008 -----------------------------------------------------------------------------------

    function test_value_is_rejected() public {
        vm.deal(address(this), 1 ether);

        // A call that carries value to a non-payable function.
        (bool ok,) = address(notary).call{value: 1}(abi.encodeCall(SignalNotary.commit, (H, uint64(940))));
        assert(!ok);

        // A plain transfer: there is no receive() and no fallback().
        (ok,) = address(notary).call{value: 1}("");
        assert(!ok);

        assert(address(notary).balance == 0);
        (,, address committer) = _commitOf(H);
        assert(committer == address(0));
    }

    // ---- FR-007, Principle II ---------------------------------------------------------------------

    function test_block_time_is_not_bar_time() public {
        // The committer says the bar closed at 100; the chain says the block is at 5_000. Neither
        // is derived from the other, and each is exactly what was set.
        vm.warp(5_000);
        notary.commit(H, 100);

        (uint64 barTs, uint64 blockTime,) = _commitOf(H);
        assert(barTs == 100);
        assert(blockTime == 5_000);
        assert(barTs != blockTime);
    }
}
