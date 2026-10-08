# Quickstart: SignalNotary

```sh
# the contract suite, offline once solc is cached
make contracts-test

# what a deploy would do, without sending anything
python -m tools.notary.deploy

# the real deploy: spends testnet MON, writes deployments/monad-testnet.json only after read-back
python -m tools.notary.deploy --broadcast

# re-read the recorded deployment from the public RPC; exit 1 with the reason if anything differs
make notary-verify

# one real commit + resolve on the deployed contract; records both transaction hashes
python -m tools.notary.smoke
```

Configuration (environment, see `.env.example`): `MONAD_RPC_URL`, `MONAD_CHAIN_ID`, `MONAD_EXPLORER_URL`,
`MONAD_NOTARY_ADDRESS` (set after a verified deploy). The signer comes from a Foundry keystore account,
never from a command-line key.
