# Research: A snapshot read resolves its snapshot against the table it reads

Each entry is a question planning had to answer, what answered it, and what was decided.

## R1. How many times does each operation load the table?

Counted with a wrapper around `Catalog.load_table` on a SQLite catalog holding three commits:
`snapshot_ids` 1, `read` 2, `read(snapshot_id=2)` 2, `current` 5, `snapshot(2)` 5, `append` 7.
**Decision:** the target is 1 for all six, and a test asserts it. *Alternatives:* trust a code
reading — rejected; the spec's own count (two, then "a third") was wrong by a factor of two.

## R2. Does `append` return the writer's own snapshot under concurrency?

It computes `_describe(snapshot_ids()[-1])` after its commit, from a **new** load, so it returns
the newest snapshot at that moment, which is another writer's if one committed in between, with no
error. **Decision:** describe from the table object the commit refreshed. *Evidence for that being
valid:* pyiceberg 0.12.0's `Table._do_commit` ends `self.metadata = response.metadata`. *Risk:* a
library upgrade could change it, hence test 3.

## R3. How wide is the race window in the deployment?

On the live `bars` table: `snapshot_ids()` 0.21 s, `read()` 1.38 s, `current()` 4.12 s (4,849
snapshots, 72,806 rows). The window is the time between the first and last load, so about 4 s for
`current`, and every `append` spends it too. **Decision:** none needed; it explains the frequency
(14 in 13 h) and why more writers makes it worse.

## R4. Would reversing the order of the two loads in `read` be enough?

It would stop `NoSuchSnapshot` in `read` (the later load only has more snapshots). It does not
touch `current`, `snapshot` or `append`, and leaves correctness depending on the order of two
statements. **Decision:** rejected as the fix; kept in mind as the reason the single-load design
is safe: any later load is a superset, so "newest of the version I hold" is always a snapshot that
exists in it.

## R5. Which callers are affected and need changing?

`current()` is called by `pipeline/replay.py` (twice), `lakehouse/research.py`, `models/registry.py`;
`snapshot()` by the registry and research; `append()`'s return by `experiments/registry.py` (the
content hash) and the DEX tables. **Decision:** none of them changes; the fix is below the API. The
return value of `append` becomes correct for them without a signature change.

## R6. Can the race be reproduced deterministically?

Yes: a wrapper around the catalog that, before returning any load after the first, commits one more
row through a second `IcebergTable` handle. Every load after the first then sees a newer version,
so each unfixed call races. *Cost:* an append is ~62 ms on SQLite, so the run is 25 reads, not the
1,000 the spec first asked for; one race is already a proof, and 25 guard against order luck.
**Decision:** spec's SC-001 amended to 25.

## R7. Is `compact()` safe against concurrent appends?

Not examined beyond reading it: it reads the newest rows and `overwrite`s the table with them. No
gap in the minute bars appears around the 21:39 and 03:39 maintenance runs. **Decision:** out of
scope; recorded as an open risk.
