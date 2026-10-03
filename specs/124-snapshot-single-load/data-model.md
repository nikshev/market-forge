# Data Model: A snapshot read resolves its snapshot against the table it reads

No stored data changes. The change is to what is handed from one step to the next.

## Table version

What one `catalog.load_table(...)` returns: the table's metadata at that moment, including its
snapshots. Held as the loaded Iceberg table object.

- **Invariant:** a later version contains every snapshot an earlier one did, plus any committed
  since. (Not true across a retention pass; out of scope.)
- **Consequence used here:** the newest snapshot *of the version held* is always present in that
  version, and cannot be resolved against any other.

## Snapshot number

The commit sequence number this system calls `snapshot_id`; Iceberg's own id is separate
(`iceberg_id`) and is what the library's scans take. Unchanged.

## Internal functions (shape only)

| name | takes | returns |
|---|---|---|
| `_ids_of(table)` | a loaded table | the snapshot numbers it holds, oldest first |
| `_in_commit_order(table, snapshot_id)` | a loaded table, a number | the rows of that snapshot, in commit order (existing; what `read` did after resolving) |
| `_describe(table, snapshot_id)` | a loaded table, a number | `TableSnapshot`, from the same table |

Public operations — `read`, `current`, `snapshot`, `append` — each hold one loaded table and call
only these.
