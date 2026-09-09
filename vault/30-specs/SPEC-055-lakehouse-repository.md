---
id: SPEC-055-lakehouse-repository
requirement: REQ-STORE-002
speckit_path: specs/055-lakehouse-repository/spec.md
status: draft
---

## Summary

[[ADR-019]] made the API depend on a repository port on 2026-09-08 and said the
durable implementation would arrive with PRD §29 "without any endpoint
changing". This is that implementation, and the promise is now something the
suite fails on: one conformance suite runs against both repositories, and every
existing endpoint test is parametrised over both.

Six more of §29.B's tables arrive with it — `channel_snapshots`,
`feature_snapshots`, `signals`, `signal_transitions`, `markets`, `setup_scores`
and `score_contributions`. §29.6 asks a channel snapshot for "quality
components" and "forecast arrays" by name, so the plane gained three container
types rather than six child tables: Arrow and Parquet carry lists and maps
natively, and DuckDB and Trino query them.

The mutation sweep found a real defect. A score's contributions were joined to
it on `as_of_ns`, and scores tie on that instant whenever the caller does not
supply one — so a market with two scores read back as one score carrying every
group either of them had. Every row was correct; the join was not. Scores carry
a content-derived id now.

## Links

- Requirement: [[REQ-STORE-002]]
- Builds on: [[REQ-STORE-001]], [[REQ-TBL-001]], [[REQ-API-001]], [[ADR-019]]
