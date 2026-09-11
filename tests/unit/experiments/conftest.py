"""Identities, registries and runs (REQ-REPRO-001)."""

from __future__ import annotations

import pytest

from channelflow.experiments import (
    CodeVersion,
    ModelAbsence,
    ModelArtifact,
    Registry,
    RunIdentity,
    config_hash,
    dataset_reference,
)
from channelflow.lakehouse import Catalog

SECOND = 1_000_000_000
COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40


def dataset(*, snapshot: int = 1, content: str = "c" * 64) -> str:
    return dataset_reference({"cex_trades": (snapshot, content)})


def identity(
    *,
    data: str | None = None,
    config: dict[str, object] | None = None,
    commit: str = COMMIT,
    dirty: bool = False,
    model: ModelArtifact = ModelAbsence.NO_MODEL,
) -> RunIdentity:
    return RunIdentity(
        dataset=data if data is not None else dataset(),
        config=config_hash(config if config is not None else {"lookback": 60}),
        code=CodeVersion(commit=commit, dirty=dirty),
        model_artifact=model,
    )


@pytest.fixture
def registry(catalog: Catalog) -> Registry:
    return Registry(catalog=catalog)
