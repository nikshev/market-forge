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
    BackupReport,
    NothingToRestore,
    RestoreReport,
    TargetNotEmpty,
    VerifyReport,
    back_up,
    restore,
    verify,
)
from channelflow.lakehouse.iceberg import (
    Catalog,
    EmptyAppend,
    IcebergTable,
    NoEventTime,
    NoSuchSnapshot,
    TableSnapshot,
    catalog,
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

__all__ = [
    "NoEventTime",
    "NoSuchSnapshot",
    "Catalog",
    "catalog",
    "TableSnapshot",
    "IcebergTable",
    "EmptyAppend",
    "verify",
    "restore",
    "back_up",
    "NothingToRestore",
    "VerifyReport",
    "TargetNotEmpty",
    "RestoreReport",
    "BackupReport",
    "Column",
    "ColumnType",
    "Schema",
    "SnapshotEmpty",
    "UnknownColumn",
    "extract",
    "query",
    "snapshot_of",
]
