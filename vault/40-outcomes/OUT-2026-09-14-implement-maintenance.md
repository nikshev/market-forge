---
id: OUT-2026-09-14-implement-maintenance
step: implement
records: [REQ-WP-070]
commit: null
---

## What was done

`_walk` over object stores, metadata pruning, `maintenance.run`, and a
`maintenance` service. 4 of 4 mutants caught, and three integration tests where
the data actually is.

## The only deletion in the system was a no-op

[[ADR-062]] makes `retention.apply` the one place that deletes. It asks
`unreferenced_files()` what nothing points at, which walked the table's
location:

    root = location.removeprefix("file://")
    if not Path(root).is_dir():
        return []

`s3://…` is not a directory, so it returned nothing — **on the storage
[[ADR-002]] makes canonical**. Retention then reported `files_removed=0`, which
is also what it reports when there is genuinely nothing to free.

Measured before the fix: expiring 933 snapshots freed zero bytes. After it, the
same table reported **721 orphans** and a pass removed 218 files while keeping
every row.

It survived because `tests/unit/lakehouse/` runs against a local warehouse where
the walk works, and nothing exercised it where it runs. The first thing this
requirement added was that test.

The walk now raises `CannotList` rather than returning `()` for a location it
cannot enumerate. An empty answer there means "nothing is orphaned", and the
difference between that and "I could not look" is the whole defect.

## Metadata was a hundred and seventeen times the data

After compaction and expiry the table still held **2.6 MB of data against 304.9
MB of metadata**. Iceberg keeps every `metadata.json` it has written unless told
not to, and each carries the full snapshot list — so N commits leave N files
whose sizes grow with N.

`write.metadata.delete-after-commit.enabled` defaults to **false**, which is why
nobody noticed. Measured on sixty commits: 61 files and 2020 KiB without it, 6
files and 710 KiB with. It is set at creation now, and the pass sets it on tables
that predate this.

## The order is not interchangeable

Prune, compact, retain. Compaction unreferences the files it replaces and removes
none; retention is what removes them. Reversed, retention finds nothing
unreferenced and compaction's output waits a whole cycle.

Two of my own tests had this wrong and taught me the rest of it: compaction alone
orphans **nothing**, because the files it replaced are still named by the
snapshots that wrote them. I had seen 721 orphans on the live table only because
I had already expired its snapshots in an earlier step. The integration test now
says so in the order it happens.

## Two guards caught me

`test_isolation.py` refused `maintenance_main` in `lakehouse/`: that package may
not import outside itself, and a plane that knew about settings and tables would
be tied to the subsystems it stores. It moved to `pipeline/`, beside the other
composition roots, which is where a composition root belongs.

And a unit test failed because a freshly created table now reports
`metadata_pruned=False` — correctly, since new tables are created with the
property. My expectation was written before the change it was testing.

## What it cost to be honest about the tool

`tools/lakehouse/compact.py` became `pipeline/maintenance_main.py`. A thing a
deployment runs continuously is not "run deliberately, never in CI", and the
image copies `src/` only — which is how the mislabelling surfaced, as a service
that could not import its own entry point.
