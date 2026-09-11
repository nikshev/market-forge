---
id: REQ-STORE-001
title: Canonical Parquet/Iceberg data plane and DuckDB research reads
type: work-package
prd_ref: "§7 Storage (target product profile), §29.0 Deployment profiles, §29.B Iceberg canonical tables"
prd_lines: "776-793, 4546-4602"
phase: null
status: implemented
depends_on: ["REQ-WP-001", "REQ-WP-002"]
tags: []
hard_gated: false
---

## Requirement

PRD §7, **Storage — target product profile**:

> - Apache Pinot: HOT realtime analytical serving
> - S3-compatible object storage: canonical durable data plane
> - Parquet: columnar physical format
> - Apache Iceberg: lakehouse table/catalog semantics for normalized/features/research data
> - Trino: distributed historical/research SQL
> - DuckDB: local/notebook/CI analytics over Parquet/Iceberg extracts
> - PostgreSQL: transactional metadata/control plane
> - ClickHouse: optional MVP/compatibility backend, not mandatory at scale

PRD §29.0, **Deployment profiles**:

> The logical schemas below are domain schemas, not a requirement that ClickHouse
> is the final system of record.
>
> - **Canonical/history:** persist normalized and derived history as Parquet/Iceberg.
> - **Research:** query Iceberg with Trino or bounded extracts with DuckDB.
>
> Any backend-specific DDL must live behind migrations/adapters and must not leak
> into signal/channel domain code.

PRD §29.B, **Iceberg canonical tables**, names the minimum set — `cex_trades`,
`cex_book_deltas`, `cex_book_snapshots`, `derivatives_funding`,
`derivatives_open_interest`, `derivatives_liquidations`, `defi_swaps`,
`defi_pool_state`, `defi_liquidity_changes`, `bars`, `feature_snapshots`,
`channel_snapshots`, `signal_candidates`, `signals`, `labels`, `backtest_runs`,
`experiment_membership` — and ends with the sentence this requirement is built
around:

> Every research-grade table must support dataset lineage/snapshot
> reproducibility.

PRD §0 item 13, restated by [[REQ-PRIN-013]]:

> All backtest/research results must be reproducible from a versioned dataset +
> config + code commit hash + model artifact hash.

[[ADR-002]] already chose this profile over §7's MVP profile and dropped
ClickHouse. This requirement is the data plane that decision promised.

## Acceptance

Table semantics (§29.B, §29.0):

- a table's history is a chain of immutable snapshots; appending data creates a
  new snapshot and changes nothing about any earlier one;
- a read at a snapshot returns exactly what that snapshot held, whatever has been
  appended since;
- a commit is atomic: a commit that loses a race, or fails part-way, leaves the
  table at its previous snapshot, and no partially written snapshot is readable;
- a snapshot names its schema, and an earlier snapshot still reads under the
  schema it was written with after the schema changes.

Lineage and reproducibility (§29.B's last line, PRD §0 item 13):

- every snapshot carries a content hash over its logical content, and identical
  content hashes to the same bytes;
- any change to the data or the schema changes the content hash;
- the content hash is stable across processes and across writer versions, so a
  research run can be identified by it later.

Point-in-time (§24.1's invariant, applied at the storage boundary):

- a point-in-time read returns nothing with an event time later than the instant
  asked for;
- a table that declares no event-time column refuses a point-in-time read rather
  than returning everything.

Research access (§29.0):

- a snapshot is queryable through DuckDB over its own Parquet files;
- no backend specifics leak into signal or channel domain code, asserted by a
  test rather than by convention.

## Scope

**In:** the object-store port and its S3 implementation, Parquet writing, the
snapshot manifest and its atomic commit, content hashing, schema versioning,
point-in-time reads, and DuckDB access to a snapshot.

**Out, and named rather than silently dropped:**

- **Pinot HOT serving** — deferred by [[ADR-002]] until a HOT serving requirement
  exists.
- **Trino** — [[ADR-002]]: it arrives when the data outgrows a single machine.
- **The full Apache Iceberg specification and a REST catalog.** What §29.B needs
  from Iceberg is table semantics — immutable snapshots, atomic commits, schema
  versioning, lineage — not its file format or its catalog protocol.
- **Migrating the API's in-memory repository onto this plane.** [[ADR-019]] made
  that a port; swapping the implementation is its own step, with its own
  requirement, and it needs data in the tables first.
- **The seventeen §29.B tables themselves.** This is the plane they sit on. Each
  table arrives with the subsystem that produces it.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-052-canonical-data-plane]]
- **Tests:**
    - `tests/integration/test_lakehouse_on_minio.py::test_a_table_commits_reads_and_time_travels_on_a_real_object_store`
    - `tests/integration/test_lakehouse_on_minio.py::test_an_earlier_read_is_unchanged_by_a_later_commit`
    - `tests/integration/test_lakehouse_on_minio.py::test_rows_come_back_in_commit_order_from_the_real_store`
    - `tests/unit/lakehouse/test_identity.py::test_a_value_cannot_forge_a_column_boundary`
    - `tests/unit/lakehouse/test_identity.py::test_changing_one_value_changes_the_identity`
    - `tests/unit/lakehouse/test_identity.py::test_each_snapshot_in_a_chain_has_its_own_identity`
    - `tests/unit/lakehouse/test_identity.py::test_negative_zero_is_not_zero`
    - `tests/unit/lakehouse/test_identity.py::test_reordering_the_columns_is_a_different_schema`
    - `tests/unit/lakehouse/test_identity.py::test_the_event_time_column_is_part_of_the_schema_identity`
    - `tests/unit/lakehouse/test_identity.py::test_the_identity_covers_the_schema`
    - `tests/unit/lakehouse/test_identity.py::test_the_identity_does_not_depend_on_the_bytes_of_the_file`
    - `tests/unit/lakehouse/test_identity.py::test_the_parquet_footer_really_does_carry_the_writer_version`
    - `tests/unit/lakehouse/test_identity.py::test_the_same_rows_get_the_same_identity_in_a_different_store`
    - `tests/unit/lakehouse/test_identity.py::test_two_types_that_print_the_same_do_not_hash_the_same`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[backtest]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[bars]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[book]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[channels]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[extrema]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[features]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[scoring]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[signals]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[stops]`
    - `tests/unit/lakehouse/test_isolation.py::test_domain_code_does_not_reach_for_a_storage_backend[turning]`
    - `tests/unit/lakehouse/test_isolation.py::test_the_lakehouse_does_not_reach_back_into_the_domain`
    - `tests/unit/lakehouse/test_point_in_time.py::test_a_point_in_time_read_before_anything_happened_is_empty_rather_than_wrong`
    - `tests/unit/lakehouse/test_point_in_time.py::test_a_point_in_time_read_composes_with_a_snapshot`
    - `tests/unit/lakehouse/test_point_in_time.py::test_a_point_in_time_read_returns_nothing_later_than_the_instant`
    - `tests/unit/lakehouse/test_point_in_time.py::test_a_table_with_no_event_time_refuses_a_point_in_time_read`
    - `tests/unit/lakehouse/test_point_in_time.py::test_the_instant_itself_is_included`
    - `tests/unit/lakehouse/test_research.py::test_a_query_at_an_older_snapshot_sees_that_snapshot`
    - `tests/unit/lakehouse/test_research.py::test_a_query_over_a_table_with_no_snapshot_is_refused`
    - `tests/unit/lakehouse/test_research.py::test_a_query_reads_every_file_a_snapshot_names`
    - `tests/unit/lakehouse/test_research.py::test_a_query_sees_only_the_files_the_snapshot_names`
    - `tests/unit/lakehouse/test_research.py::test_a_result_can_name_the_dataset_it_read`
    - `tests/unit/lakehouse/test_research.py::test_a_snapshot_is_queryable_by_the_table_s_own_name`
    - `tests/unit/lakehouse/test_research.py::test_the_extract_does_not_outlive_the_query`
    - `tests/unit/lakehouse/test_schema.py::test_a_boolean_is_not_an_integer`
    - `tests/unit/lakehouse/test_schema.py::test_a_column_is_reachable_by_name_and_an_unknown_one_is_not`
    - `tests/unit/lakehouse/test_schema.py::test_a_column_type_outside_the_vocabulary_is_refused`
    - `tests/unit/lakehouse/test_schema.py::test_a_container_column_refuses_the_wrong_shape`
    - `tests/unit/lakehouse/test_schema.py::test_a_decimal_column_takes_a_decimal_and_nothing_else`
    - `tests/unit/lakehouse/test_schema.py::test_a_float_list_hashes_by_its_order`
    - `tests/unit/lakehouse/test_schema.py::test_a_float_map_hashes_the_same_whatever_order_it_was_built_in`
    - `tests/unit/lakehouse/test_schema.py::test_a_row_carrying_a_column_the_schema_does_not_declare_is_refused`
    - `tests/unit/lakehouse/test_schema.py::test_a_row_missing_a_column_is_refused`
    - `tests/unit/lakehouse/test_schema.py::test_a_schema_names_the_columns_a_reader_has_to_convert_back`
    - `tests/unit/lakehouse/test_schema.py::test_a_schema_names_the_map_columns_a_reader_has_to_convert`
    - `tests/unit/lakehouse/test_schema.py::test_a_schema_with_no_columns_is_refused`
    - `tests/unit/lakehouse/test_schema.py::test_a_string_list_cannot_forge_its_own_boundaries`
    - `tests/unit/lakehouse/test_schema.py::test_a_value_of_the_wrong_python_type_is_refused`
    - `tests/unit/lakehouse/test_schema.py::test_an_event_time_column_has_to_be_a_nanosecond_count`
    - `tests/unit/lakehouse/test_schema.py::test_an_event_time_column_that_does_not_exist_is_refused`
    - `tests/unit/lakehouse/test_schema.py::test_an_integer_is_accepted_where_a_float_is_declared`
    - `tests/unit/lakehouse/test_schema.py::test_duplicate_columns_are_refused`
    - `tests/unit/lakehouse/test_schema.py::test_two_decimals_that_compare_equal_are_different_content`
- **Code:**
    - `src/channelflow/lakehouse/__init__.py`
    - `src/channelflow/lakehouse/iceberg.py`
    - `src/channelflow/lakehouse/research.py`
    - `src/channelflow/lakehouse/schema.py`
- **Outcomes:** [[OUT-2026-09-09-implement-canonical-data-plane]], [[OUT-2026-09-09-plan-canonical-data-plane]], [[OUT-2026-09-09-requirement-canonical-data-plane]], [[OUT-2026-09-09-spec-canonical-data-plane]]
<!-- trace:end -->

## Notes

Hand-written rather than extracted: PRD §46 has no work package for §29, and
`tools/extract_prd.py` does not read §7 or §29. The same is true of
[[REQ-API-001]], [[REQ-BT-001]], [[REQ-CHAN-001]] and [[REQ-SCORE-001]], which
were written the same way from PRD sections that no work package covers.

The acceptance criteria above are **derived** where the PRD states properties
rather than tests — "immutable snapshots", "dataset lineage/snapshot
reproducibility", "must not leak into domain code" — and quoted where it states
them outright. This section is human territory and is never machine-rewritten.
