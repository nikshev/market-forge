// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

// @trace: REQ-INFRA-006
// Only the Foundry cheatcodes SignalNotary.t.sol uses. Vendored instead of depending on forge-std so a
// fresh checkout needs no git submodule. Cheatcode address: keccak256("hevm cheat code").
interface Vm {
    struct Log {
        bytes32[] topics;
        bytes data;
        address emitter;
    }

    function prank(address caller) external;
    function expectRevert(bytes4 selector) external;
    function expectRevert() external;
    function warp(uint256 timestamp) external;
    function deal(address who, uint256 newBalance) external;
    function recordLogs() external;
    function getRecordedLogs() external returns (Log[] memory logs);
}
