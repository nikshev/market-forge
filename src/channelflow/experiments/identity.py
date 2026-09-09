"""PRD §0 item 13's four components, and what makes a run reproducible.

# @trace: REQ-REPRO-001

    "Усі результати backtest/research повинні відтворюватися з versioned dataset
     + config + code commit hash + model artifact hash."

Four hashes, and the interesting part is what happens when one of them is not
available. Three failure modes look identical in a record that only stores
strings:

- a run that fits no model, so there is no artifact to hash;
- a run that fitted one and nobody wrote the artifact down;
- a run whose commit hash was taken from a working tree with uncommitted
  changes.

The first is fine and reproducible. The second and third are not, and both are
easy to produce by accident -- the third especially, because `git rev-parse
HEAD` answers cheerfully in a dirty tree and the answer names a tree that does
not exist anywhere.

So a component is present or explicitly absent, never merely missing, and the
absence says which kind it is. That is [[ADR-037]]'s rule; the vocabulary here
is its own because "this run fits no model" and "nobody recorded who issued this
bridge" are the same shape and not the same statement.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum

#: A 40-character hexadecimal SHA-1, which is what `git rev-parse HEAD` gives.
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class ModelAbsence(StrEnum):
    """Why a run has no model artifact hash. The two are opposites."""

    #: The run fits nothing. A statistical comparison, an ablation over fixed
    #: features, a replay: there is no artifact and there was never going to be.
    NO_MODEL = "no_model"
    #: A model was fitted and its artifact was not recorded. The run cannot be
    #: reproduced, and this value is what says so instead of a blank.
    UNRECORDED = "unrecorded"


#: A hash, or a stated reason there is none.
ModelArtifact = str | ModelAbsence


class NotReproducible(ValueError):
    """A run is missing something PRD §0 item 13 requires."""


@dataclass(frozen=True)
class CodeVersion:
    """Which commit produced a result, and whether that is the whole truth.

    `dirty` is not a nicety. `git rev-parse HEAD` in a tree with uncommitted
    changes returns a real commit hash for code that was not the code that ran,
    and a result recorded against it is unreproducible in the specific way that
    looks most convincing -- the hash resolves, the commit exists, the diff is
    gone.
    """

    commit: str
    dirty: bool

    def __post_init__(self) -> None:
        if not _COMMIT.match(self.commit):
            raise ValueError(
                f"{self.commit!r} is not a 40-character commit hash; an abbreviated "
                "or invented one cannot be resolved later, which is the only thing "
                "recording it is for"
            )

    @property
    def reproducible(self) -> bool:
        return not self.dirty


@dataclass(frozen=True)
class RunIdentity:
    """The four components, and whether they add up to a reproducible run."""

    #: A dataset component from `dataset_reference`: which tables at which
    #: snapshots.
    dataset: str
    #: From `config_hash`.
    config: str
    code: CodeVersion
    model_artifact: ModelArtifact

    def __post_init__(self) -> None:
        for name in ("dataset", "config"):
            value = getattr(self, name)
            if not value:
                raise ValueError(
                    f"{name} is empty; a run with no {name} identity cannot be "
                    "replayed, and an empty string would record that it can"
                )

    @property
    def missing(self) -> tuple[str, ...]:
        """Which components stop this run being reproducible, in the PRD's order.

        All of them, not the first: a caller who fixes one and re-runs should not
        discover the next one the same way.
        """
        gaps: list[str] = []
        if not self.code.reproducible:
            gaps.append(
                "code commit: the working tree had uncommitted changes, so the "
                "recorded commit names a tree that never ran"
            )
        if self.model_artifact is ModelAbsence.UNRECORDED:
            gaps.append("model artifact: a model was fitted and its artifact hash was not recorded")
        return tuple(gaps)

    @property
    def reproducible(self) -> bool:
        return not self.missing

    @property
    def run_hash(self) -> str:
        """This run's own identity, over all four components.

        Includes the dirty flag: a result produced from a dirty tree is not the
        same run as one produced from the commit it names, and giving them one
        identity would let the second silently stand in for the first.
        """
        digest = hashlib.sha256()
        for part in (
            self.dataset,
            self.config,
            self.code.commit,
            "dirty" if self.code.dirty else "clean",
            str(self.model_artifact),
        ):
            payload = part.encode()
            digest.update(len(payload).to_bytes(4, "little"))
            digest.update(payload)
        return digest.hexdigest()

    def require_reproducible(self) -> None:
        """Raise unless every component PRD §0 item 13 names is there."""
        gaps = self.missing
        if gaps:
            raise NotReproducible(
                "this run cannot be reproduced from what was recorded -- " + "; ".join(gaps)
            )
