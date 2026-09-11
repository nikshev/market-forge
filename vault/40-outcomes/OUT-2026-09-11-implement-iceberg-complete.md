---
id: OUT-2026-09-11-implement-iceberg-complete
step: implement
records: [REQ-WP-039, REQ-WP-037]
commit: null
---

## What was done

The hand-rolled canonical plane is gone. `table.py`, `store.py` and
`snapshot.py` are deleted, along with the suites that tested their mechanics.
`backup.py` was rewritten for the Iceberg layout, and [[REQ-STORE-001]]'s
guarantees — point-in-time reads, snapshot isolation, content identity — moved
with their traces onto `iceberg.py` and the suites that still assert them.

[[REQ-WP-039]] reaches `implemented`. 1735 tests pass, integration included.

## The decision I made, and how to reverse it

[[ADR-061]]: **a backup restores where it came from.** Iceberg's metadata holds
absolute URIs, so a tree restored elsewhere names a place that holds nothing.
The alternative — rewriting every URI across the metadata JSON and the Avro
manifests — puts us back inside the one part of the format [[ADR-060]] adopted
Iceberg in order to stop owning, in the code path that runs when everything else
has already failed.

[[REQ-WP-037]]'s acceptance is narrowed **in the requirement**, not quietly in
the tests. Losing a bucket's contents is still recoverable; restoring under a
different name is not. If that capability is ever needed, the ADR names the work
and can be superseded rather than worked around.

## The gap that nearly shipped

The first Iceberg backup copied files with `shutil`. Against the local warehouse
the unit tests use, every test passed. Against MinIO — the storage this system
actually runs on — it could not see an `s3://` path at all, and `verify`
reported **every file missing**: a false disaster, produced by the tool whose
job is to tell you whether you have a real one.

The integration test found it, which is the whole argument for CLAUDE.md's two
gates. Both now read and write through Iceberg's own `FileIO`, the same client
the table commits through, and the round trip runs against the bucket in CI.

I had written that gap into a test as a *deliberate limitation*, with a docstring
explaining why refusing was honest. It was not honest; it was a backup that did
not back up. Naming a hole carefully is not the same as not having one.

## The defect deletion uncovered

**The content hash did not cover the schema.** The old format mixed the schema
fingerprint into its digest; the first Iceberg version hashed only rows. Two
datasets holding the same values under different columns would have shared an
identity, and a run could have cited the wrong dataset and still verified. Found
because a test of the old format asserted it, and deleting that test meant
deciding whether the property survived. It does now, with its own test.

## The duck-typing trap

Migrating `research.py` left its tests green **without touching them**: the
shared fixtures still handed them the old `Table`, and both classes answer
`name`, `current`, `read` and `snapshot`. Structural typing made the migration
cheap and made that possible. Naming the fixtures apart was the fix, and it is
worth remembering that a green suite during a migration proves less than usual.

## What is still open

- **[[REQ-WP-038]]** — retention — is unblocked and unstarted. Iceberg supplies
  the delete and the expiry; removing what nothing references is ours, over
  [[ADR-059]]'s capability.
- **Where the catalog lives on the stack.** Nothing constructs a PostgreSQL
  catalog yet; the integration tests use SQLite with an S3 warehouse, which
  proves the storage and not the catalog.
- **Restoring under a different name**, per [[ADR-061]].
- **Reading costs one plan per snapshot**, which is fine now and will not be at
  thousands.
