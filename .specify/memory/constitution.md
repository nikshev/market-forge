# ChannelFlow Constitution

The PRD (`channel_flow_prd_codex_ua_v5.md`) is the source of truth. These
principles are non-negotiable and apply to every spec, plan and implementation.

## I. No look-ahead, ever

Any feature computed at timestamp `t` uses only data with `event_time <= t`,
and only values that were actually available in real time at the moment of
decision. This holds even when violating it would improve a backtest.
A backtest improvement is never evidence that a leak is acceptable.

## II. Time is not one thing

`event_time`, `exchange_time`, `block_time`, `ingest_time`, `bar_open_time`
and `bar_close_time` are distinct and never conflated. Every model carrying a
timestamp names which one it holds.

## III. History is immutable

Finalized channel snapshots and signal snapshots are never rewritten. A
correction is a new record, not an edit.

## IV. Baselines before models

No ML or GMDH layer is added until deterministic baselines exist and leakage
tests pass. A model that cannot beat a deterministic baseline is not a result.

## V. Calibration, not accuracy

Any signal carrying a probabilistic score reports calibration metrics.
Accuracy alone is not an acceptable evaluation of a probability.

## VI. Every feature is documented

A feature declares its semantics, unit, cadence, source, freshness and leakage
policy. An undocumented feature is not done.

## VII. Live and replay are the same code

Code is deterministic in backtest mode and maximally identical between live
and replay. Divergence between the two is a defect, not a configuration.

## VIII. Connectors share one interface

Every new exchange or DEX connector implements the common canonical interface.

## IX. No automatic execution

Phases 1-3 form signals and alerts only. The system does not open positions.

## X. Thresholds are configuration

All numeric thresholds are configurable. Hard-coded trading thresholds are
forbidden outside test fixtures.

## XI. Results are reproducible

Every backtest and research result is reproducible from a versioned dataset,
config, code commit hash and model artifact hash.

## XII. Correctness precedes performance

Correctness, replay parity and data integrity are settled before any
performance optimization.

## XIII. Work is incremental

The system is built in the phases and against the acceptance criteria the PRD
defines, not ahead of them.

## XIV. Everything is traceable

Every unit of work carries a requirement ID from `vault/10-requirements/`
through spec, test and implementation. Work that cannot be traced is not done.
