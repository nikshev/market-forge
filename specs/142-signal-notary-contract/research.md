# Research: SignalNotary contract

Resolved before design. Date 2026-10-08. "Measured" means run on this host today.

## R1. How does a `.sol` test earn a `VERIFIES` edge?

**Facts.** `tools/trace/collect.py:33` — `CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".yml", ".yaml"}`
decides which tracked files can carry `# @trace:`. `VERIFIES` comes from pytest markers on tests that
*passed* in `make markers`. Neither sees Solidity.

**Decision.** A pytest module runs `forge test --json` once (module-scoped fixture), holds the explicit
list of forge test names the spec requires, and has one `@pytest.mark.trace("REQ-INFRA-006")` case per name
that asserts that forge test's `status == "Success"`. A further case asserts the forge run contains no test
that is not in the list (so an unlisted test cannot drift in unnoticed) and that the list is non-empty.

**Why not the alternatives.** Widening `CODE_SUFFIXES` changes the graph's meaning repo-wide. A single "forge
exited 0" case passes on an empty suite. Python-side EVM simulation (py-evm) would test a re-implementation,
not the Solidity.

**Measured.** `forge test --json` on a scratch project returned per-test `{"status":"Success",...}` keyed by
`file:Contract` then `test_name()`; one call, ~2 s including a first `solc 0.8.28` download.

## R2. Is Foundry available, and does it need the network?

**Measured.** `forge`/`cast` 1.7.1 are installed. A scratch project with `solc_version = "0.8.28"` compiled
and ran a test; `solc` was fetched on first use (the host has network). RPC `https://testnet-rpc.monad.xyz`
answers (`cast chain-id` → 10143, client `Monad/0.16.3`).

**Consequence.** Tests need the network once, to fetch the compiler, and not afterwards. The spec's "no
network" is about the chain, and stays true; the compiler cache is the exception and is documented.

## R3. Python chain client: web3.py or `cast`?

For this feature the chain traffic is: chain id, balance, a create transaction, a receipt, `getCode`, one
`call`, and two `send`s in the smoke run. `cast` does each in one command. web3.py would add a dependency
tree for the same calls. The runtime client that [[REQ-INFRA-007]] needs (signing, nonce management, an
outbox that drains) is a different problem with different requirements and is decided there.

## R4. EVM version and compiler

Monad is EVM-bytecode-compatible; its docs recommend a recent EVM version. The contract uses no opcode newer
than `cancun` (`block.timestamp`, storage, events). `cancun` is the conservative choice that compiles with
`solc 0.8.28` and runs on Monad. If the deploy is rejected for an opcode, the failure is immediate and
visible, not silent.

## R5. Keeping the key out of argv

`forge create --private-key <hex>` puts the key in the process list, readable by any user on the host. Foundry
supports encrypted keystores (`cast wallet import`, `--account`, `--password-file`) and signer environment
variables. The first task confirms the supported mechanism on 1.7.1 and the tool builds its argv from it;
`test_chain.py` asserts the built argv contains no 64-hex-digit token and not the key value. The current key
sits in `/root/.monad/deployer.env` (mode 600, outside the repository); it will be moved into a keystore
rather than read from a plain env file at deploy time.

## R6. What exactly does "deployed code equals compiled code" compare?

`forge inspect SignalNotary deployedBytecode` against `cast code <address>`. With no `immutable` and no
linked library, the deployed runtime bytecode equals the compiler's runtime output, including the metadata
tail (which is deterministic for the same sources and settings). Comparison is of the keccak of each, so the
record can hold the 32-byte hash instead of kilobytes. If Monad were to alter code on deployment this
comparison would fail loudly, which is the point.

## R7. Is a block timestamp trustworthy as "time of commit"?

It is the validator-assigned block time, bounded by the chain's consensus rules, and is what the product may
cite ("no later than"). It is not `bar_close_time`, and the contract keeps both. How far apart they are is
measured on testnet in [[REQ-INFRA-007]], not assumed here.

## R8. Faucet funds

Account `0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131` holds 5 MON (read back from chain 10143 on 2026-10-08).
A create plus a smoke commit and resolve costs a small fraction of that; the balance is re-read immediately
before broadcasting.
