---
id: OUT-2026-09-11-spec-plan-dataset-lineage
step: plan
records: [REQ-WP-040]
commit: null
---

## What was done

`specs/078-dataset-lineage/`: spec, checklist, plan, data model, contract and
quickstart. [[REQ-WP-040]] moves through `specified` to `planned` in one step,
because the spec and the plan were written together and pretending otherwise
would be theatre.

## What was decided

- **Three outcomes, not two.** `RESOLVED`, `CHANGED`, `GONE`. A resolver that
  only asked whether the snapshot id still exists would pass `CHANGED` — a name
  that resolves over different rows — and that is exactly the case a citation
  exists to catch. An id is a name; a hash is a claim about what was under it.
- **`GONE` is not an error.** A registration whose dataset has been expired
  still records a run that happened, and refusing to read it would make every
  report unreadable after a legitimate retention pass. The sharper version of
  that trade — whether `require_registered` should refuse a stale citation — is
  left open rather than decided quietly.
- **The origin is supplied, never inferred.** A layer that re-derived it would
  ask the table what it holds *now*, which is the right answer to a different
  question and wrong exactly when the table has moved on.
- **No default on the field** ([[ADR-015]]), which makes thirteen fields against
  §23.9's eleven. [[ADR-058]] added the twelfth for the same kind of reason: the
  list describes the artifact and §0 governs.

## What is still open

- **Whether a stale citation should be fatal at the point of use.**
- **One dataset per registration**, which is right today and will not be if a
  study ever spans several tables.
