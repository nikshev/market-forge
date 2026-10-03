# Contract: reading a snapshot of an Iceberg table

For `IcebergTable.read`, `.current`, `.snapshot` and the value `.append` returns.

1. **One version.** Each call loads the table from the catalog **once**. Every id and every row it
   reports comes from that one load.
2. **Newest means newest of that version.** The snapshot chosen as newest is present in the version
   read, whatever commits land afterwards.
3. **Missing is loud.** A snapshot number the version does not hold raises `NoSuchSnapshot`, with the
   message `<table> has no snapshot <n>; it has <ids of the version read>`.
4. **Pinned is stable.** A read pinned to a snapshot that exists returns the same rows however many
   commits follow.
5. **Empty is empty.** A table nothing has been committed to reads as the empty result and has no
   current snapshot.
6. **`append` returns what it committed.** The returned `TableSnapshot` is the snapshot this call
   wrote, not the newest at the time it returns.
7. **No tolerance.** No caller catches `NoSuchSnapshot` to compensate for a race; none is needed.
