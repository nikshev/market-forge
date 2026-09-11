"""The canonical data plane: Parquet on object storage, with table semantics.

# @trace: REQ-STORE-001

PRD section 7's target storage profile, which [[ADR-002]] chose over the MVP
profile on the first day of the project: S3-compatible object storage as the
canonical durable data plane, Parquet as the physical format, Iceberg semantics
for tables, DuckDB for bounded research extracts.

What "Iceberg semantics" means here is the four properties section 29.B needs
and not the file format that carries them elsewhere: immutable snapshots, atomic
commits, versioned schemas, and a dataset identity a research run can be pinned
to. [[ADR-053]] records why that identity is a hash of the rows rather than of
the files.

Nothing in this package is imported by signal or channel domain code, which is
PRD section 29.0's rule -- "any backend-specific DDL must live behind
migrations/adapters and must not leak into signal/channel domain code" -- and is
asserted by a test rather than left to care.
"""

from channelflow.lakehouse.backup import (
    BackupConflict,
    BackupReport,
    RestoreReport,
    TargetNotEmpty,
    VerifyReport,
    WouldLandShort,
    back_up,
    restore,
    verify,
)
from channelflow.lakehouse.research import (
    SnapshotEmpty,
    extract,
    query,
    snapshot_of,
)
from channelflow.lakehouse.schema import (
    Column,
    ColumnType,
    Schema,
    UnknownColumn,
)
from channelflow.lakehouse.snapshot import (
    DataFile,
    ManifestTampered,
    Snapshot,
)
from channelflow.lakehouse.store import (
    ConditionalWritesUnsupported,
    InMemoryObjectStore,
    KeyExists,
    KeyMissing,
    ObjectStore,
    S3ObjectStore,
)
from channelflow.lakehouse.table import (
    COMPRESSION,
    COMPRESSION_LEVEL,
    VERSION_DIGITS,
    CommitRaceLost,
    NoEventTime,
    NoSuchSnapshot,
    SchemaMismatch,
    Table,
)

__all__ = [
    "verify",
    "restore",
    "back_up",
    "WouldLandShort",
    "VerifyReport",
    "TargetNotEmpty",
    "RestoreReport",
    "BackupReport",
    "BackupConflict",
    "COMPRESSION",
    "COMPRESSION_LEVEL",
    "VERSION_DIGITS",
    "Column",
    "ColumnType",
    "CommitRaceLost",
    "ConditionalWritesUnsupported",
    "DataFile",
    "InMemoryObjectStore",
    "KeyExists",
    "KeyMissing",
    "ManifestTampered",
    "NoEventTime",
    "NoSuchSnapshot",
    "ObjectStore",
    "S3ObjectStore",
    "Schema",
    "SchemaMismatch",
    "Snapshot",
    "SnapshotEmpty",
    "Table",
    "UnknownColumn",
    "extract",
    "query",
    "snapshot_of",
]
