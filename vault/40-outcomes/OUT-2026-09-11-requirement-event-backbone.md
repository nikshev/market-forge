---
id: OUT-2026-09-11-requirement-event-backbone
step: requirement
records: [REQ-WP-042]
commit: null
---

## What was done

[[ADR-063]] and `vault/10-requirements/REQ-WP-042.md`. The question was which
queue fits; the answer needed two decisions, and only one of them was about the
broker.

## What the research settled

Checked against documentation rather than recalled:

- **Redpanda's Iceberg Topics** — a topic materialised straight into an Iceberg
  table — requires Tiered Storage, and both are **enterprise-licensed**.
- **The Apache Iceberg Kafka Connect sink** is official and Apache-2.0, and its
  catalogs are REST, Hive, Glue, Nessie and BigQuery Metastore. Ours is
  `pyiceberg`'s SQL catalog ([[ADR-060]], verified in [[REQ-WP-041]]), so the
  only catalog both a Java connector and `pyiceberg` can share is REST —
  adopting the sink means replacing the catalog with a REST service.
- **Redpanda Community Edition** is BSL, converting to Apache 2.0 four years
  after each merge; self-hosted production is permitted, reselling it as a
  service is not.

## What decided it, and it was not the licence

Both alternatives would write our tables while knowing none of our rules.
`IcebergTable` refuses an empty append, computes [[ADR-053]]'s content hash over
rows, and reconstructs commit order from sequence numbers; [[ADR-056]] requires
a per-series watermark before any entry point writes. A connector honours none
of it and would produce tables that look identical and carry no guarantees, with
the first symptom being a replay writing the same bars twice — the defect
[[ADR-056]] exists because of.

**The rule a connector would break is the one written down precisely so a future
writer could not break it by accident.**

## What makes the broker choice safe to make now

Redpanda speaks the Kafka protocol, so moving to Apache Kafka changes a compose
file and a bootstrap address rather than application code. A decision that costs
a compose file to reverse does not have to be right the first time, and saying
so is more useful than defending it.

## What is marked unverified

How Pinot's real-time tables consume a topic in detail. The pages read were
introductory, Pinot is deferred by [[ADR-002]], and nothing here depends on it
beyond the topic speaking the Kafka protocol — which is the reason to
standardise on the protocol rather than on a product.
