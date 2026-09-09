---
id: OUT-2026-09-09-implement-canonical-data-plane
step: implement
records: [REQ-STORE-001]
commit: null
---

## What was done

`channelflow.lakehouse`: the object-store port and its S3 adapter, a typed
schema with a fingerprint, immutable snapshots with a content hash, a table that
commits atomically, and bounded DuckDB extracts. 80 unit tests, 4 integration
tests against MinIO, 25 mutations.

[[ADR-002]] chose this storage profile on the project's first day and nothing
had built it since. The API has been reading from an in-memory repository
([[ADR-019]]) with a note saying the durable one arrives with §29.

## The measurement behind [[ADR-053]]

The obvious dataset identity is a digest of the files. It is wrong here, and the
reason is measurable: `pq.write_table` puts `parquet-cpp-arrow version 25.0.1`
into every footer on this machine, so identical rows written after a `pyarrow`
upgrade are different bytes. Compression settings do the same — the default and
`zstd` produce different files for the same data.

A dataset identity with that property fails exactly when it matters. A research
run recorded today stops matching its own dataset after a dependency bump, and
nothing about the data changed. Every comparison keyed by dataset —
[[REQ-EXP-015]]'s "same walk-forward folds", [[REQ-EXP-017]]'s "exact same
immutable entry signals" — would start reporting library releases as
differences.

So the content hash is over the rows in the schema's own encoding, and each file
also carries a digest of its bytes, in a separate field, answering the separate
question of whether that object is the one that was written. A test asserts the
footer really does carry the writer version, so if a future Parquet writer stops
embedding it, something notices and the ADR becomes worth revisiting.

## The commit, and the race that had to be built

A commit is one conditional write: the manifest for version N+1 goes to a key
that must not already exist. There is no current-snapshot pointer, because a
pointer needs its own atomicity and can disagree with the manifests it points
at; the newest snapshot is simply the highest manifest version present.

Testing the race needed a store wrapper. Two writers racing means both read the
same current snapshot and both try to commit the next version — and sequentially
that cannot happen, because the second writer re-reads and picks a later one. The
collision has to be injected at the only instant it can occur, between computing
the version and writing its manifest. The test installs a rival's objects exactly
there, and then asserts what matters: the loser raises, the winner's snapshot is
current, and the loser's data file sits in the store unreferenced where no query
can see it.

## What the sweep corrected

Twenty-four of twenty-five mutations were caught. The survivor is the useful one.

Removing the zero-padding from manifest version keys changed no test — because
`snapshot_ids` parses each version and sorts the integers, so nothing in this
code depends on the listing's lexical order. The code's own comment claimed the
opposite ("zero-padded so a lexical listing is a numeric ordering") and so did
the test written to cover it. Both said something that was not true of the code
they described.

Both now say what is: the padding is kept for the people and tools that browse
the bucket and *do* sort lexically, and it is not what makes the chain correct.
That correction is the whole return on running the sweep, and it is the second
time today a comment turned out to be describing an intention rather than the
code beneath it.

## What was decided

- **A snapshot exists exactly when its manifest does**, which makes "no partially
  written snapshot is readable" true by construction rather than by care.
- **A table with no event-time column refuses a point-in-time read.** Returning
  everything would answer a different question in a way the caller could not
  detect.
- **A backend that cannot do conditional writes is refused at the moment of the
  write**, not emulated. An emulation makes every commit look atomic and loses
  the races it exists to catch.
- **A boolean is not an integer.** Python says `True == 1` and
  `isinstance(True, int)`; a schema that agreed would let a flag column accept
  counts and vice versa.
- **The extract is a context manager.** Files left behind would be a second copy
  of the canonical plane that nothing tracks, and the first stale read from it
  would look exactly like a correct one.

## Mutation results

Twenty-five mutations, twenty-four caught, every restore verified. The one that
survived is recorded because it changed the code:

| Mutation | Caught by |
| --- | --- |
| The manifest is written unconditionally | `test_a_commit_that_loses_the_race_leaves_the_table_where_it_was` |
| The manifest is written before its data file | `test_a_data_file_without_a_manifest_is_not_a_snapshot` |
| The identity is over the file bytes | `test_the_identity_does_not_depend_on_the_bytes_of_the_file` |
| The identity ignores the schema | `test_the_identity_covers_the_schema` |
| The identity depends on the file order | `test_the_identity_does_not_depend_on_the_order_the_files_are_listed_in` |
| A tampered manifest is accepted | `test_a_manifest_edited_after_it_was_committed_is_refused` |
| A non-integer manifest field is coerced | `test_a_manifest_whose_counts_are_not_integers_is_refused` |
| **Manifest versions are not zero-padded** | **nothing — see above; the padding is not load-bearing and the comments now say so** |
| The point-in-time filter excludes its own instant | `test_the_instant_itself_is_included` |
| A table with no event time answers a point-in-time read | `test_a_table_with_no_event_time_refuses_a_point_in_time_read` |
| A snapshot drops its parent's files | `test_a_query_reads_every_file_a_snapshot_names` |
| An empty append is allowed | `test_an_append_of_no_rows_is_refused` |
| An append under another schema is allowed | `test_an_append_under_a_different_schema_is_refused` |
| The recorded event time is the batch minimum | `test_the_recorded_event_time_is_the_batch_maximum` |
| A missing column is defaulted | `test_a_row_missing_a_column_is_refused` |
| The row encoding drops its type tags | `test_two_types_that_print_the_same_do_not_hash_the_same` |
| The row encoding is separated rather than length-prefixed | `test_a_value_cannot_forge_a_column_boundary` |
| A store without conditional writes falls back | `test_a_backend_that_cannot_do_conditional_writes_is_refused` |
| A missing key reads as empty bytes | `test_the_s3_store_reports_a_missing_object_as_missing` |
| The in-memory listing is unsorted | `test_listing_is_by_prefix_and_sorted` |
| The extract is left behind | `test_the_extract_does_not_outlive_the_query` |
| The query reads whatever is under the data prefix | `test_a_query_sees_only_the_files_the_manifest_names` |
| The current snapshot is the oldest | `test_a_read_at_a_snapshot_ignores_everything_appended_since` |
| The s3 listing leaks its prefix | `test_the_prefix_is_added_on_the_way_in_and_taken_off_on_the_way_out` |
| A boolean passes as an integer | `test_a_boolean_is_not_an_integer` |

## What is still open

- **Nothing writes to this plane.** It is the floor PRD §29.B's seventeen tables
  stand on, and every one of them is a separate piece of work.
- **The API still reads from memory.** [[ADR-019]] made that a port so the
  implementation could be swapped; swapping it needs data in the tables first.
- **A manifest lists every file in the table, its parent's included**, so it
  grows linearly with the number of commits. Iceberg answers that with manifest
  lists and compaction. Nothing needs them yet, and a table with a hundred
  thousand commits would.
- **There is no delete, no update and no compaction.** §29.B's tables are
  append-only event history, which is why; a table that ever needs a correction
  needs a design for one, and this is not it.
- **`Table.read` materialises every file into memory.** Bounded extracts are
  DuckDB's job and it streams, but `read` does not — a table larger than memory
  has to be queried rather than read.
