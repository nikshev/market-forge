---
id: OUT-2026-09-11-implement-iceberg
step: implement
records: [REQ-WP-039]
commit: null
---

## What was done

`lakehouse/iceberg.py`: an Iceberg-backed table with the surface the hand-rolled
one has, plus the file accounting retention needs. `pyiceberg[sql-sqlite]` added.
16 tests, 16 of 16 mutants caught, fast gate still green with no services.

RED first: the test module failed to import `IcebergTable`.

**[[REQ-WP-039]] stays `planned`.** This is step one of a staged migration: no
caller has moved and the old format is still here. The requirement closes when
the last caller moves and the hand-rolled format is gone.

## What the sweep found

Fourteen mutants died against the first test set. The two survivors were the
same omission twice — asserting a count where the thing that matters is which:

- **The delete cutoff applied to the wrong side of the comparison.** Rows at
  1, 2, 3, 4 with a cutoff of 3: keeping `>= 3` leaves two rows and keeping
  `< 3` leaves two rows. The test asserted `num_rows == 2` and passed for both.
  It now asserts which event times survived.
- **`unreferenced_files` consulting only the newest snapshot.** Invisible in a
  test that expires the history first, because then there is only one snapshot
  left. The new test does the delete **without** the expiry and asserts that
  nothing is unreferenced — which is the middle link of the chain and the one
  easiest to miss: after a delete the current snapshot has dropped the old
  files, and every snapshot before it still holds them, and they are as live as
  it is. Nothing is removable until that history is expired.

That test is worth more than the mutant that prompted it. It states, as an
executable fact, why retention is three operations rather than two.

## What was measured rather than argued

- **A point-in-time read composes two dimensions.** A backfilling second commit
  separates them: by snapshot gives what was known, by event-time filter gives
  what had happened, and Principle I names both in one sentence. The
  hand-rolled `read` already composed them and the composition carried over.
- **Concurrency is Iceberg's, and it is better than what it replaces.** Two
  writers from one parent: the old layer refuses the loser, Iceberg retries and
  lands it. Refusing a valid append because another writer was faster is a
  dropped write, which in a concurrent ingestion path is a defect wearing a
  guarantee's clothes. The spec's FR-004 was corrected to what is actually
  needed — commits serialise, nothing half-applied, no rows lost.

## What changed that somebody will notice

**Content hashes differ from the old format's.** The old digest was over
per-file digests; this one is over rows, sorted, in the schema's canonical
encoding. [[ADR-053]]'s rule — identity is the rows, never the bytes — is
preserved and strengthened: the new hash is also independent of how many commits
the rows arrived in, which the old one was not. A test asserts exactly that, and
it is the test that shows the two readings coming apart.

## What is still open

- **No caller has moved**, and a half-migrated plane is a state to leave
  quickly. Next steps: the domain tables, then the API repositories, then the
  registries, then deleting `table.py`.
- **Backup and restore** ([[REQ-WP-037]]) are written against the old layout and
  will need their Iceberg equivalent. Their central argument survives: the copy
  order is the writer's order, inverted for removal.
- **Where the catalog lives on the stack**, and who creates the namespace.
- **[[REQ-WP-038]]** is unblocked but not started.
