# Quickstart: notarizing records

```sh
# build the images with the commit baked in (a dirty tree produces only unnotarizable records)
make notary-build-info                       # prints the CHANNELFLOW_CODE_COMMIT / _DIRTY exports (not the epoch: that is set once, in .env)

# run the pass as before; the worker now registers what it writes (no key, no chain access)
docker compose up -d --no-deps --build worker notary

# what is waiting, and why
python -m channelflow.notary.main outbox     # unbatched, unconfirmed, unnotarizable (with reasons)

# check one record against the chain
python -m channelflow.notary.verify snapshot|binance|BTCUSDT|300000000000|1791450000000000000
python -m channelflow.notary.verify export <record_id> > bundle.json     # a third party needs only this
python -m channelflow.notary.verify bundle bundle.json                   # public RPC only

# the figure the product may quote
python -m channelflow.notary.latency --since 1h > deployments/monad-testnet-latency.json
```

Configuration: `CHANNELFLOW_NOTARY_ENABLED`, `…_FROM`, `…_INTERVAL`, `…_BATCH_WINDOW` (default `30m`),
`…_MAX_BATCH`, `…_MIN_BALANCE`, `…_MAX_GAS_PRICE`, `…_GAS_MARGIN`, `…_CONFIRMATION` (default `finalized`), `MONAD_RPC_URL`,
`MONAD_CHAIN_ID`, `MONAD_NOTARY_ADDRESS`, and the two secret *paths* for the keystore and its password.
