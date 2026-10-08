# The signal notary

A short account of what is notarized, what a commit proves and what it does not. The mechanism is
specified for third parties in `specs/143-notarize-final-records/contracts/notary-bundle.md`.

## What is notarized

Every **final channel snapshot** and every **decision** the system takes, including the decision *not*
to alert. A decision is one step in a candidate's history; a candidate that ends — invalidated or expired
— without ever having alerted is recorded as a `NO_ALERT` with the reason it ended. Each record is hashed
together with the three things a result is reproducible from: the configuration of the pass that
produced it, the input dataset it was computed from, and the code commit it ran as.

Records are grouped into batches and one Merkle root per batch is written to the `SignalNotary`
contract on Monad testnet. Anyone holding a record, its context and the inclusion proof can check
it against the chain without trusting this system: `python -m channelflow.notary.verify`.

## What a commit proves

That the record existed **no later than** the block that holds its batch's root. It does not prove
that a signal preceded a price move; nothing here claims that. A signal is as early as the block that
holds it, and the figure below says how long that took.

## How long it takes

A record reaches the chain after four waits in a row: the bar is built into its timeframe by `resample`
(the 5-minute series was about 45 minutes behind the clock when measured), the worker's cycle records
it (28–35 minutes), the batch window closes (up to 30 minutes), and the block follows within a second.
Only the last two are the notary's. The figure the product may quote is measured on the running system,
per record, from the chain's own time, and it is the whole path:

Measured: median 5653 s, p95 6553 s, max 6870 s over 168 records.

That is a median of about 94 minutes, from the close of a bar to the block that holds it. The sample is
168 records across 5 series over 65 minutes of block times, on 2026-10-08, after the first batch was
set aside: its records had been registered late because of an unrelated failure of the worker that day.
The numbers are in `deployments/monad-testnet-latency.json`, and a test makes this paragraph quote that file
exactly. A faster path means a faster pipeline upstream (the notary adds at most its window), not a faster
notary.

## What is not covered

* The `suppression` kind (an alert the freshness gate refused to send) is defined and tested, but the
  running worker delivers no alerts yet, so nothing produces one.
* History before the notary was switched on is not notarized (`CHANNELFLOW_NOTARY_FROM`).
* The testnet can be reset; the contract is then redeployed from the same source and the record in
  `deployments/monad-testnet.json` replaced.
