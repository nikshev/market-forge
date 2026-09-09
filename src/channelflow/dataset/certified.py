"""The dataset a model is allowed to see.

# @trace: REQ-US-007
# @trace: REQ-WP-017

REQ-US-007 asks for "a guarantee that the training dataset contains no feature
leakage". Every check that guarantee needs already existed in `leakage.py` and
already ran -- in tests, by hand, wherever someone chose to call them. A check
someone has to remember is not a guarantee, and this failure is silent: a
dataset whose labels were knowable at `t` trains fine, scores well, and every
metric downstream reads like an edge.

So the check becomes the only way to obtain the thing training accepts. A
`CertifiedDataset` cannot be constructed around an unclean report -- a gate with
a back door is documentation, and the first person in a hurry walks through it.

This is the fourth time this repository turns a prohibition nobody can verify
into a structure that cannot be violated: [[ADR-022]]'s transform declaration,
[[ADR-027]]'s inert regime label, [[ADR-040]]'s lead-lag import ban, and this.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.dataset.folds import Fold
from channelflow.dataset.leakage import LeakageReport, RowLike, check_folds, check_rows


class CertificationRefused(ValueError):
    """The dataset did not pass, so nothing may train on it."""


@dataclass(frozen=True)
class CertifiedDataset:
    """Folds that passed both leakage checks, and the reports that say so.

    The folds are held here rather than read from the caller: a caller who
    certifies a dataset and then edits their own list would otherwise train on
    something the certificate does not describe.
    """

    folds: tuple[Fold, ...]
    rows: LeakageReport
    folds_report: LeakageReport

    def __post_init__(self) -> None:
        unclean = [r for r in (self.rows, self.folds_report) if not r.clean]
        if unclean:
            findings = "; ".join(f"{f.rule}: {f.detail}" for r in unclean for f in r.findings)
            raise CertificationRefused(
                f"a certificate cannot be built around an unclean report: {findings}"
            )


def certify(rows: list[RowLike], folds: list[Fold]) -> CertifiedDataset:
    """Run both checks and hand back what training accepts.

    Refuses on any finding, and names them. An empty dataset refuses too --
    every "no row violates X" check passes over nothing, and an empty dataset is
    the most likely output of a broken build ([[ADR-025]]).
    """
    rows_report = check_rows(rows)
    folds_report = check_folds(folds)
    return CertifiedDataset(folds=tuple(folds), rows=rows_report, folds_report=folds_report)
