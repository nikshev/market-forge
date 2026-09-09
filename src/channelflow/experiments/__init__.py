"""Run identity, the experiment registry, and the gate between them and a result.

# @trace: REQ-REPRO-001
# @trace: REQ-BIAS-011

PRD §0 item 13 wants every research result reproducible from four things, and
PRD §41 rule 11 wants every discarded variant stored. [[ADR-053]] built the
first of the four hashes; this package is the other three, the registry that
holds them on the canonical plane, and the gate that turns both rules from
statements into refusals.

The registry is a lakehouse table, so its history is immutable and its commits
are atomic without asking. A registry that could be tidied up after the fact
would defeat the rule it exists to enforce.
"""

from channelflow.experiments.hashing import (
    ConfigValue,
    UnhashableConfig,
    config_hash,
    dataset_reference,
)
from channelflow.experiments.identity import (
    CodeVersion,
    ModelAbsence,
    ModelArtifact,
    NotReproducible,
    RunIdentity,
)
from channelflow.experiments.registry import (
    SCHEMA,
    TABLE_NAME,
    Outcome,
    RecordedRun,
    Registry,
    Run,
)
from channelflow.experiments.report import CherryPicked, Report, publish, why_not

__all__ = [
    "SCHEMA",
    "TABLE_NAME",
    "CherryPicked",
    "CodeVersion",
    "ConfigValue",
    "ModelAbsence",
    "ModelArtifact",
    "NotReproducible",
    "Outcome",
    "RecordedRun",
    "Registry",
    "Report",
    "Run",
    "RunIdentity",
    "UnhashableConfig",
    "config_hash",
    "dataset_reference",
    "publish",
    "why_not",
]
