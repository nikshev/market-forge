# Phase 1 — Data model

## `StudyResult`

| Field | Meaning |
|---|---|
| `comparison` | what the run found — per-fold reports and their aggregate |
| `identities` | one `RunIdentity` per variant, all four components populated |
| `registrations` | PRD §23.9 entries, one per variant |
| `report` | the gate's report, or `None` when nothing beat the base rate |
| `reliability` | calibration per horizon over the validated rows |
| `scored_folds` | how many folds contributed |

`comparison` is returned rather than dropped: the identities say the run is
citable and the comparison says what it discovered, and a caller needs both.

## `Score.artifact`

`str | None`, defaulted. `None` when the comparison did not fit that model —
two experiments hand in predictions computed elsewhere, and reporting an
artifact for them would name a model that did no work.

## `report_comparison(model=...)`

One `ModelArtifact` for the whole field, or a mapping of them. A variant absent
from the mapping falls back to `NO_MODEL`, which is the honest answer for a
variant nothing fitted.
