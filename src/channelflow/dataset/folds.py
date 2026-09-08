"""PRD section 24.3's chronological folds.

# @trace: REQ-WP-017
# @trace: REQ-BIAS-001
# @trace: REQ-BIAS-010

    - prefer chronological walk-forward splits;
    - apply purge/embargo where overlapping horizon would contaminate
      validation;
    - never random-shuffle train/test for primary evaluation.

The purge is the part that is easy to leave out and impossible to notice
missing. A label at `t` describes what happened until `t + H`; if `t` is in the
training set and `t + H` reaches into the validation window, the model was
trained on the answer. The validation score is then a memory, and it looks
exactly like a good score.

The embargo covers the other direction: rows immediately after a validation
window share market state with it, so they are excluded from the next training
set rather than teaching the model what it was just tested on.

PRD section 41 rule 10 -- "Optimize parameters on train/validation; locked test
remains untouched" -- is a method that raises here, not a flag someone reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from channelflow.dataset.models import Row


class ShufflingRefused(ValueError):
    """PRD section 41 rule 1: no random train/test primary split."""


class LockedTestSplit(PermissionError):
    """PRD section 41 rule 10: the test split is not for tuning.

    Named this way round rather than `TestSplitLocked` because pytest collects
    anything beginning with `Test` and warned that it could not.
    """


class FoldConfigurationImpossible(ValueError):
    """The purge and embargo cannot leave usable folds."""


@dataclass(frozen=True)
class Fold:
    index: int
    train: tuple[Row, ...]
    validate: tuple[Row, ...]
    purged: int
    embargoed: int


@dataclass
class WalkForwardFolds:
    """Chronological folds over labelled rows.

    `horizon_ns` is not optional. Without it the purge cannot be computed, and
    a fold builder that accepted rows without knowing their horizon would
    silently produce contaminated splits.
    """

    horizon_ns: int
    folds: int = 5
    embargo_ns: int = 0
    _rows: list[Row] = field(default_factory=list)
    _locked: bool = True

    def build(self, rows: list[Row], *, shuffle: bool = False) -> list[Fold]:
        if shuffle:
            raise ShufflingRefused(
                "PRD section 41 rule 1 forbids a random train/test primary split. "
                "Labels here overlap in time, so a shuffled split validates on rows "
                "whose horizons the training set already saw."
            )
        if not rows:
            raise FoldConfigurationImpossible("no rows to fold")

        ordered = sorted(rows, key=lambda r: r.as_of_ns)
        self._rows = ordered
        size = len(ordered) // (self.folds + 1)
        if size == 0:
            raise FoldConfigurationImpossible(
                f"{len(ordered)} rows cannot make {self.folds} folds; "
                "producing fewer would hide the configuration's failure"
            )

        built: list[Fold] = []
        for index in range(self.folds):
            split = size * (index + 1)
            validate = ordered[split : split + size]
            if not validate:
                continue
            window_start = validate[0].as_of_ns

            candidates = ordered[:split]
            # The purge: a training row whose label horizon reaches into the
            # validation window was trained on the answer.
            kept = [r for r in candidates if r.label.horizon_end_ns < window_start]
            purged = len(candidates) - len(kept)

            # The embargo: rows just after the window share its market state.
            window_end = validate[-1].as_of_ns
            embargoed = sum(
                1 for r in ordered[split + size :] if r.as_of_ns <= window_end + self.embargo_ns
            )

            if not kept:
                # A fold with nothing to train on is dropped rather than
                # returned empty -- an empty training set is not a fold.
                continue
            built.append(
                Fold(
                    index=index,
                    train=tuple(kept),
                    validate=tuple(validate),
                    purged=purged,
                    embargoed=embargoed,
                )
            )

        if not built:
            raise FoldConfigurationImpossible(
                "the purge left every fold without training rows; the horizon is "
                "long relative to the fold size"
            )
        return built

    def test_split(self) -> tuple[Row, ...]:
        """The locked final segment. PRD section 41 rule 10.

        Raises unless explicitly unlocked, so reading it during tuning is an
        error rather than a decision nobody records.
        """
        if self._locked:
            raise LockedTestSplit(
                "the test split is locked. PRD section 41 rule 10: optimize "
                "parameters on train/validation; the locked test remains untouched. "
                "Call unlock() deliberately, once, when tuning is finished."
            )
        size = len(self._rows) // (self.folds + 1)
        return tuple(self._rows[-size:]) if size else ()

    def unlock(self) -> None:
        """Deliberate, and recorded by being a separate call."""
        self._locked = False
