---
id: OUT-2026-09-11-implement-iceberg-research
step: implement
records: [REQ-WP-039]
commit: null
---

## What was done

Step three, partial: `lakehouse/research.py` moved to the Iceberg table, and the
suites that test the *old* format now take explicitly named legacy fixtures so
nothing passes for the wrong reason.

The old format is still here. Step three cannot finish, and the reason is below.

## The duck-typing trap this step walked into and out of

Migrating `research.py` to `IcebergTable` left its tests **green without
touching them** — because the shared fixtures still handed them the old `Table`,
and both classes answer `name`, `current`, `read` and `snapshot`. The suite said
the migration worked while testing the thing being replaced.

Structural typing is what made the migration cheap and it is also what made that
possible. The fix is naming: `trades` and `config` are Iceberg, `legacy_trades`
and `legacy_config` are the format being replaced, and a test that wants the old
one has to say so.

`test_a_query_sees_only_the_files_the_manifest_names` was rewritten rather than
re-pointed, because its property survives and its mechanism does not. It plants
an orphan parquet in the table's own directory — which is exactly what a
retention pass leaves between its delete and its cleanup — and asserts the query
still counts one row.

## PLANNING STOPPED: backup cannot restore elsewhere any more

[[REQ-WP-037]]'s backup is location-independent. Its keys are relative
(`cex_trades/data/...`), so a restore can land in a different bucket, a
different endpoint or a local directory, and three of its tests turn on exactly
that.

**Iceberg writes absolute URIs.** Measured:

    "location": "file:///var/folders/.../channelflow/x"
    "manifest-list": "file:///var/folders/.../snap-...avro"

A tree copied elsewhere and restored there is unreadable: every pointer in the
metadata still names where it used to live. Same-location restore works, and is
the ordinary Iceberg backup model. Restoring somewhere else needs every absolute
URI rewritten across the metadata JSON **and** the Avro manifest lists, and
`pyiceberg` 0.12 offers no such operation.

So [[ADR-060]] costs a guarantee that already exists, which the ADR did not
anticipate and which is not mine to trade away:

- **Same-location restore only.** Honest, standard, and a reduction: "restore to
  a new bucket" stops being possible, and three of [[REQ-WP-037]]'s tests
  describe behaviour that is gone.
- **Write the path rewriting.** Keeps the guarantee. It means parsing and
  rewriting Iceberg's own metadata, which is the one part of the format that
  was supposed to become somebody else's tested problem.

Both are defensible. The first is cheaper and quietly narrows what disaster
recovery can do; the second is real work in the most delicate part of the
format. That is a decision about how much this system is willing to depend on
one storage location, and it belongs to whoever owns the deployment.

## What is still open

- **The choice above**, which blocks deleting the old format: `backup.py` is
  written against it, and [[REQ-WP-037]] is `implemented`, so deleting its code
  would make that status a lie.
- **`table.py`, `store.py` and their suites** stay until then.
- **Where the catalog lives on the stack.**
