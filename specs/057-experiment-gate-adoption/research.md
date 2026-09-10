# Phase 0 — Research

Three questions had to be answered before the design could be written. Each was
answered by running code, not by reading it.

## 1. Can a variant's configuration be recovered at all?

**Decision**: yes — `dataclasses.asdict(variant)` plus the variant's type name.

**Rationale**: every variant object in the research package is a frozen
dataclass. Checked across the field: `RollingOLSChannel`, `HuberChannel`,
`QuantileChannel`, `KalmanChannel`, `AblationArm`. `config_hash` accepts the
result unchanged, including `None` values and nested tuples.

The decisive check was two variants of one class:

    RollingOLSChannel(bands="std")                 -> 3d41bf7f…
    RollingOLSChannel(bands="residual_quantiles")  -> different

These are two of `MODELS`' five and they differ in one field. Any design that
hashed the variant's *name* would have given them the same config, and the
registry would have held two indistinguishable rows for two genuinely different
runs — full coverage by row count, and worthless.

**Alternatives considered**:
- *Hash the variant's name within the experiment.* Cheapest, and wrong for the
  reason above. Worse than no coverage, because it reads as checked.
- *Ask the caller for each variant's config.* Pushes onto every caller a thing
  the comparison already knows, and a caller who gets it wrong is not detectable.

## 2. Where does a field come from when the caller injects it?

**Decision**: the comparison keeps the config of each variant it was handed, at
the moment it runs it.

**Rationale**: 11 of the 18 entry points accept an injected field —
`compare_channel_models(models=…)`, `run_ablation(arms=…)`,
`compare_stop_policies(policies=…)` and eight more. For those, the variant
objects belong to the caller and today the reports keep only a name. A report
that reconstructed the config from the *default* field would be right for the
default call and silently wrong for every injected one, which is the worst of
the available failure modes: correct in every test that does not pass `models=`.

**Alternatives considered**:
- *Look the name up in the module's default field.* Rejected above.
- *Refuse injected fields.* Would break every test that narrows a comparison to
  two variants for speed, and removes a capability to serve a bookkeeping rule.

## 3. How is "reporting twice" prevented on an append-only registry?

**Decision**: skip any variant whose `run_hash` is already in `registry.hashes()`.

**Rationale**: [[ADR-056]] settled the general rule the day before this work —
every pipeline entry point reads a watermark and writes only past it, because
the plane rejects nothing. For a series the watermark is a timestamp; for a
registry it is set membership, and `hashes()` already exists and already returns
a `frozenset`. A run hash covers all four components, so two runs with the same
hash are the same run by construction.

**Alternatives considered**:
- *Record unconditionally.* Contradicts ADR-056 and doubles a registry on a
  re-run, which is exactly the defect found in `REQ-PIPE-001`.
- *A timestamp watermark, as the replay uses.* Wrong shape: an experiment's
  `as_of_ns` is the caller's and two experiments can share it.

## Non-question: does the gate change?

No. `publish` and `Registry` are used exactly as [[REQ-REPRO-001]] built them.
If adoption turns out to need the gate to change, that is a finding about the
gate and gets recorded as one rather than absorbed into this work.
