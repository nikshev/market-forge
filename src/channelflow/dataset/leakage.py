"""The checks that say whether a dataset is honest.

# @trace: REQ-WP-017
# @trace: REQ-BIAS-001
# @trace: REQ-BIAS-003
# @trace: REQ-BIAS-004

Separate from the modules it checks, deliberately. A checker living inside the
thing it checks tends to be written to pass: it sees the same intermediate
state, and the temptation is to assert on that rather than on the output. This
takes a built dataset and knows nothing else about how it was made.

Every check here is of the form "no row violates X", and ADR-025 is why that
matters: such a check passes trivially over an empty dataset, and an empty
dataset is the most likely output of a broken build. A build that silently
produced nothing, followed by a report saying everything is clean, reads
exactly like success.

So the report carries what each rule *examined*, not only what it found, and an
empty dataset fails.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from channelflow.dataset.folds import Fold
from channelflow.dataset.models import LabelClass


class LabelLike(Protocol):
    label_class: LabelClass
    horizon_end_ns: int
    available_ns: int
    extremum_time_ns: int | None


class RowLike(Protocol):
    """What the checker needs to read, and nothing more.

    Deliberately not `Row`. `Row` refuses these violations at construction, so
    a checker that only accepted `Row` could never see one -- it would be
    untestable, and untestable in a way that looks like it works.

    The checker exists for rows arriving from somewhere the type did not guard:
    a Parquet file, a database, a future implementation of this module. A
    protocol is what lets it say so.
    """

    entity: str
    as_of_ns: int
    features: dict[str, float]
    source_max_event_ns: int
    label: LabelLike


@dataclass(frozen=True)
class Finding:
    """One violation, named precisely enough to fix."""

    rule: str
    detail: str
    row_index: int | None = None
    field: str | None = None


@dataclass(frozen=True)
class LeakageReport:
    findings: tuple[Finding, ...]
    #: Rule name to the number of rows it examined. "Clean" means something was
    #: checked; a rule that silently applied to nothing is visible here rather
    #: than indistinguishable from one that passed.
    examined: dict[str, int]

    @property
    def clean(self) -> bool:
        return not self.findings


def check_rows(rows: list[RowLike]) -> LeakageReport:
    """PRD section 24.2's rule, over the built rows."""
    findings: list[Finding] = []

    if not rows:
        # ADR-025. The message says empty, not clean.
        return LeakageReport(
            findings=(
                Finding(
                    rule="non_empty",
                    detail=(
                        "the dataset has no rows. Every other check here passes "
                        "trivially over nothing, so this is reported as a failure "
                        "rather than as a clean result"
                    ),
                ),
            ),
            examined={"non_empty": 0},
        )

    for index, row in enumerate(rows):
        if row.source_max_event_ns > row.as_of_ns:
            findings.append(
                Finding(
                    rule="feature_not_after_t",
                    detail=(
                        f"row sourced from {row.source_max_event_ns}, after its "
                        f"as-of time {row.as_of_ns}"
                    ),
                    row_index=index,
                    field="source_max_event_ns",
                )
            )
        if row.label.horizon_end_ns <= row.as_of_ns:
            findings.append(
                Finding(
                    rule="label_is_in_the_future",
                    detail=(
                        f"label horizon ends at {row.label.horizon_end_ns}, at or "
                        f"before the row's own time {row.as_of_ns}"
                    ),
                    row_index=index,
                    field="label.horizon_end_ns",
                )
            )
        if (
            row.label.extremum_time_ns is not None
            and row.label.available_ns < row.label.extremum_time_ns
        ):
            findings.append(
                Finding(
                    rule="label_available_at_confirmation",
                    detail=(
                        f"label available at {row.label.available_ns} but its "
                        f"extremum occurred at {row.label.extremum_time_ns}; PRD "
                        "section 41 rule 3 requires availability to be the "
                        "confirmation time"
                    ),
                    row_index=index,
                    field="label.available_ns",
                )
            )
        if row.label.available_ns <= row.as_of_ns:
            findings.append(
                Finding(
                    rule="label_not_known_at_t",
                    detail=(
                        f"label was available at {row.label.available_ns}, at or "
                        f"before the row's own time {row.as_of_ns}: a label already "
                        "knowable at t is a feature, not a target"
                    ),
                    row_index=index,
                    field="label.available_ns",
                )
            )

    return LeakageReport(
        findings=tuple(findings),
        examined={
            "feature_not_after_t": len(rows),
            "label_is_in_the_future": len(rows),
            "label_available_at_confirmation": sum(
                1 for r in rows if r.label.extremum_time_ns is not None
            ),
            "label_not_known_at_t": len(rows),
        },
    )


def check_folds(folds: list[Fold]) -> LeakageReport:
    """PRD section 24.3's rule, over the built folds."""
    findings: list[Finding] = []

    if not folds:
        return LeakageReport(
            findings=(
                Finding(
                    rule="non_empty",
                    detail="no folds to check; see ADR-025",
                ),
            ),
            examined={"non_empty": 0},
        )

    for fold in folds:
        if not fold.validate:
            continue
        window_start = fold.validate[0].as_of_ns
        for row in fold.train:
            if row.as_of_ns >= window_start:
                findings.append(
                    Finding(
                        rule="train_precedes_validation",
                        detail=(
                            f"fold {fold.index}: a training row at {row.as_of_ns} is "
                            f"not before the validation window starting at "
                            f"{window_start}"
                        ),
                        field="as_of_ns",
                    )
                )
            if row.label.horizon_end_ns >= window_start:
                findings.append(
                    Finding(
                        rule="horizon_purged",
                        detail=(
                            f"fold {fold.index}: a training row's label horizon ends "
                            f"at {row.label.horizon_end_ns}, inside the validation "
                            f"window starting at {window_start}. The model was "
                            "trained on the answer."
                        ),
                        field="label.horizon_end_ns",
                    )
                )

    return LeakageReport(
        findings=tuple(findings),
        examined={
            "train_precedes_validation": sum(len(f.train) for f in folds),
            "horizon_purged": sum(len(f.train) for f in folds),
        },
    )
