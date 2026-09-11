# Phase 0 — Research

## 1. Copy by listing, or by walking snapshots?

**Decision**: walk snapshots, oldest first; within each, data files then its
manifest.

**Rationale**: listing every key under the table prefix and copying it is
shorter and wrong. A sorted listing returns `<table>/metadata/v00000001.json`
before `<table>/data/...`, so the naive implementation copies manifests first —
precisely the ordering `table.py` calls corruption. The bug would be invisible
in any test that lets the copy finish.

Walking also yields the interruption property without extra work: stop at any
point and the copy is a prefix of the history in which every manifest is fully
backed by the data it names.

## 2. What does verification actually check?

**Decision**: presence, byte digest, and snapshot identity — reported apart.

**Rationale**: each answers a different question and they fail for different
reasons. A missing file is the corruption the ordering prevents. A byte mismatch
is transit damage, and retrying may help. An identity mismatch means a different
dataset arrived, and retrying will not.

Byte digests are checked despite [[ADR-053]]'s warning, because the warning is
about comparing *re-encoded* data. A copy re-encodes nothing, so byte equality
is genuinely expected here and a mismatch is genuinely a defect. Identity still
uses the content hash, which is what a restore *means*.

## 3. Why not a `copy` operation on the port?

**Decision**: `get` then `put_if_absent`, through the existing port.

**Rationale**: a server-side copy is faster and exists on S3, but adding it to
`ObjectStore` would put an operation in the port that `InMemoryObjectStore` has
to emulate and that the table layer does not need. The port is deliberately "what
the table layer needs from durable storage, and nothing more". Using
`put_if_absent` also makes a re-run of an interrupted backup safe by
construction: an object already copied is not copied again, and an object copied
with different content raises rather than being overwritten.

## 4. What happens when a restore would land short?

**Decision**: refuse, unless the caller named that snapshot.

**Rationale**: restoring to an earlier point is a legitimate request and, done
by accident, is indistinguishable from it afterwards. The refusal is not
paternalism: the caller who wants snapshot 5 says `5`, and the caller who says
nothing gets either the newest or an error — never a quiet older one.

"Landing short" is detectable because the backup's own manifests say what the
newest snapshot was when the copy finished.

## 5. Where does the round trip run?

**Decision**: logic on the in-memory store, round trip on MinIO in CI.

**Rationale**: the argument `REQ-STORE-001` already made — a double that raises
the error it was told to raise proves the mapping, not the guarantee. A backup
is the one feature that must work against the real backend, and CLAUDE.md's
two-gate rule puts it in the full gate.
