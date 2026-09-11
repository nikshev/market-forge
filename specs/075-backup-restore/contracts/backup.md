# Contract — backup and restore

```python
back_up(name, *, source: ObjectStore, target: ObjectStore) -> BackupReport
restore(name, *, source: ObjectStore, target: ObjectStore,
        snapshot_id: int | None = None) -> RestoreReport
verify(name, *, store: ObjectStore, expect_content_hash: str | None = None) -> VerifyReport
```

## Guarantees

- Every data file is copied before the manifest naming it, so an interrupted
  backup is a prefix of the history and never a manifest over absent data.
- A re-run copies only what is missing and raises rather than overwriting an
  object whose content differs.
- `restore` refuses a target holding anything under the table's prefix.
- `restore` refuses to land short of the backup's newest snapshot unless that
  snapshot was named, and always reports where it landed.
- `verify` distinguishes a missing file, a byte-digest mismatch and a content
  identity mismatch, and reports all three rather than the first.
- An orphan object — present, named by no manifest — is not a failure, matching
  the writer's own rule.
- Nothing reads a clock.

## Does not

Schedule anything, decide retention, encrypt, or touch Postgres. The canonical
plane is object storage; the rest is named in the requirement's derivation as
deliberately out of scope.
