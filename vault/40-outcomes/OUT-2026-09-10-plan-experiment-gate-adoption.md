---
id: OUT-2026-09-10-plan-experiment-gate-adoption
step: plan
records: [REQ-BIAS-011]
commit: null
---

## What was done

`specs/057-experiment-gate-adoption/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/seam.md`, `quickstart.md`. Constitution Check passes with no
violations, so Complexity Tracking is empty and was removed.

The seam itself is built, because [[REQ-BIAS-011]] is `hard_gated: true` and
`/sdd-plan` step 4 forbids `planned` for such a requirement: the failing test
comes first and the status goes straight to `tested`.

**RED, before `src/channelflow/experiments/fields.py` existed:**

    tests/unit/experiments/test_fields.py:10: in <module>
        from channelflow.experiments import (
    E   ImportError: cannot import name 'Field' from 'channelflow.experiments'
    ERROR tests/unit/experiments/test_fields.py
    !!!!!! Interrupted: 1 error during collection !!!!!!
    1 error in 0.08s

17 tests, green after the seam was written. mypy clean at 162 files.

## What was decided

- **The field comes from the variant objects, through `dataclasses.asdict`.**
  Checked before planning rather than assumed: every variant in the research
  package is a frozen dataclass, `config_hash` accepts what comes out (`None`
  and nested tuples included), and the two `RollingOLSChannel` variants that
  differ only in `bands` hash differently. That last check is the whole argument
  against hashing the variant's *name*, which would have collided them.
- **The comparison keeps the config of what it was handed, not what its module
  defaults to.** 11 of the 18 entry points accept an injected field. A report
  that reconstructed a config from the module's defaults would be right for the
  default call and silently wrong for every injected one — correct in every test
  that does not pass `models=`, which is the worst available failure mode.
- **Idempotence is set membership, not a timestamp.** [[ADR-056]] settled the
  rule the day before; for a registry the watermark is `hashes()`, because an
  experiment's `as_of_ns` is the caller's and two experiments can share one,
  while a run hash covers all four components.
- **The seam records before it publishes.** The gate refuses a winner whose
  field is not on record, so publishing first would make every experiment's
  first report fail.
- **`research` will import `experiments`, and that direction is the decision.**
  Neither imports the other today — checked. The mechanism stays ignorant of
  every experiment, which is what lets a nineteenth arrive without touching it.

## What is still open

- **Nothing is adopted yet.** This step built the seam and its tests; the
  eighteen modules still neither declare `EXPERIMENT`/`COMPARISON` nor expose a
  `field`. `tests/unit/research/test_gate_adoption.py` — the discovered check
  that makes FR-012 true — is deliberately not written yet, because it cannot be
  green until the last module adopts and a red suite cannot be committed.
- **Adding a config to each comparison's entries changes those dataclasses'
  equality.** Existing tests that compare entry objects may break. How many is
  unknown until the change is made, and it is the main thing that could make the
  implement step larger than the plan suggests.
- **Two `Field` guards duplicate refusals the gate already makes** (a winner
  outside its field; a duplicated variant). That is deliberate — the comparison
  should not be able to construct the refusal — but it means the same rule is
  now stated in two places and could drift.
