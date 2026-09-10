# Phase 1 — Data model

No new entities and no schema change. Two existing declarations change shape.

## `EXEMPT` (new, in `extrema/causality.py`)

| Field | Type | Rule |
|---|---|---|
| key | `str` | module path relative to `src/channelflow/`, e.g. `extrema/causality.py` |
| value | `str` | why a forbidden helper is legitimate there |

Both halves are load-bearing. The key is a module rather than a package so an
exemption cannot cover the file beside the one that needed it. The value is
required because an exemption without a reason is indistinguishable from an
oversight, and it is what the next reader has to disagree with.

An entry naming a module that does not exist fails the suite: a list that has
stopped describing anything still reads as authority.

## `FeatureSpec.point_in_time_safe`

`bool` → `Literal[True]`.

The field stays required and stays written out by the author, so [[ADR-015]]'s
reasoning holds. What changes is that the only writable value is the one the
rule permits, which turns a claim into a constraint.
