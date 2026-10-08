# Data model: notary tables

Four append-only lakehouse tables, in the lakehouse's own `Schema`/`Column` vocabulary. Nothing is updated; the
state of anything is the latest event about it. Times are nanoseconds and named (Principle II).

## `notary_records` — one row per registered record (immutable)

Event-time column: `bar_close_time_ns`.

| Column | Type | Meaning |
|---|---|---|
| `bar_close_time_ns` | timestamp_ns | `bar_close_time` of the record's bar (a decision: of the bar that caused the transition) |
| `record_id` | string | identity, see below; unique |
| `kind` | string | `snapshot` · `decision` · `suppression` |
| `venue`, `symbol` | string | series (decisions: of the candidate) |
| `timeframe_ns` | int64 | |
| `record_hash` | string | hex SHA-256 of the envelope; empty when `notarizable` is false |
| `record_bytes` | string | the record's canonical bytes, hex |
| `scheme_version` | int64 | hash-scheme version (1) |
| `config_hash` | string | `config_hash(...)` of the pass configuration |
| `dataset_ref` | string | `dataset_reference({"bars": (id, content_hash)})` |
| `dataset_snapshot_id` | int64 | the pinned bars snapshot id (to re-read the input) |
| `code_commit` | string | 40 hex, or empty when absent |
| `notarizable` | string | `yes` or `no` |
| `reason` | string | why not, when `no` (absent commit, dirty tree, unhashable config, non-final) |
| `registered_at_ns` | int64 | `ingest_time`-class: when the registrar wrote it; informational, never hashed |

`record_id` — snapshot: `snapshot|<venue>|<symbol>|<timeframe_ns>|<as_of_ns>`; decision:
`decision|<signal_id>|<ordinal>`; suppression: `suppression|<signal_id>|<queued_at_ns>`.

### Decision row (the canonical record of a decision)

`DECISION_SCHEMA`, encoded with `Schema.encode_row`:

| Column | Type | |
|---|---|---|
| `bar_close_time_ns` | timestamp_ns | the bar that caused the transition |
| `signal_id` | string | |
| `ordinal` | int64 | position in the candidate's history |
| `venue`, `symbol` | string | |
| `timeframe_ns` | int64 | |
| `direction`, `boundary` | string | |
| `from_state`, `to_state` | string | |
| `reason` | string | the transition's recorded reason |
| `verdict` | string | `ALERT` (to `alerted`) · `NO_ALERT` (to `invalidated`/`expired` and never alerted) · `STEP` (any other) |
| `alerted_before` | string | `yes`/`no` |

A snapshot's canonical record is `channels.to_row(...)` under `channels.SCHEMA` — the existing row, not a copy.

## `notary_batches` — one row per formed batch (immutable)

Event-time column: `max_bar_close_time_ns`.

| Column | Type | Meaning |
|---|---|---|
| `max_bar_close_time_ns` | timestamp_ns | latest leaf bar close; its whole-second value is the contract's `barTs` |
| `batch_root` | string | hex root; the batch's identity |
| `leaf_count` | int64 | |
| `min_bar_close_time_ns` | int64 | earliest leaf |
| `formed_at_ns` | int64 | when the batcher formed it (informational) |
| `window_ns` | int64 | the window in force (configuration at the time) |

## `notary_leaves` — membership (immutable)

Event-time column: `bar_close_time_ns`.

| Column | Type | |
|---|---|---|
| `bar_close_time_ns` | timestamp_ns | the leaf's own bar close (the latency is measured from this) |
| `batch_root` | string | |
| `ordinal` | int64 | leaf index in the tree (order: bar close, kind, record_id) |
| `record_id` | string | |
| `record_hash` | string | |

A record is in at most one batch (checked on formation).

## `notary_events` — the outbox log (append-only)

Event-time column: `event_at_ns` (the local time of the event; the *chain's* time is a separate column).

| Column | Type | |
|---|---|---|
| `event_at_ns` | timestamp_ns | when the service wrote the event |
| `batch_root` | string | |
| `event` | string | `formed` · `submitted` · `confirmed` · `failed` · `held` |
| `attempt` | int64 | |
| `tx_hash` | string | for `submitted`, `confirmed` |
| `nonce` | int64 | for `submitted` |
| `block_number` | int64 | for `confirmed` |
| `block_time_s` | int64 | chain-assigned seconds, for `confirmed` |
| `detail` | string | error text, or the reason it is `held` (balance, gas price) |

**Derived outbox state of a batch** = its latest event: `formed`/`failed`/`held` → pending, `submitted` →
in flight, `confirmed` → done. A record with no leaf row is *unbatched*. A record with `notarizable = no` is
*unnotarizable* and appears in the outbox listing with its reason.

## Metrics

`channelflow_notary_unbatched_records`, `channelflow_notary_unconfirmed_batches`,
`channelflow_notary_oldest_pending_age_seconds`, `channelflow_notary_unnotarizable_records`,
`channelflow_notary_balance_wei`, `channelflow_notary_last_confirmed_block_time_seconds`.
