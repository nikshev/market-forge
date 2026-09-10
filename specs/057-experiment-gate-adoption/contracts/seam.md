# Contract — the seam

The one function through which a comparison becomes registry rows.

```
report_comparison(
    comparison,          # anything satisfying Compared
    *,
    experiment: str,
    dataset: str,        # from a Recording, or dataset_reference(...)
    code: CodeVersion,   # the caller's, never read from git here
    registry: Registry,
    model: ModelArtifact = NO_MODEL,
    as_of_ns: int,
) -> Reported
```

## Behaviour

1. Reads `comparison.field`.
2. Builds one `RunIdentity` per variant: the caller's `dataset`, `code` and
   `model`, and `config_hash(that variant's config)`. The variants therefore
   differ in exactly the component that differed.
3. Drops any variant whose `run_hash` is already in `registry.hashes()`.
4. Records the rest — every one of them, whatever its outcome — with
   `Outcome.KEPT` for `chosen` and `Outcome.DISCARDED` for the others.
5. If `field.chosen` is not `None`, calls `publish(...)` with the whole field
   and returns its `Report`. Otherwise returns no report.

## Returns

`Reported`: `recorded: int`, `skipped: int`, `report: Report | None`.

`skipped` is counted rather than silent, for [[ADR-056]]'s reason: a re-run is a
no-op and should look like one.

## Refuses

- A field whose variant config cannot be hashed — `UnhashableConfig` propagates.
  A variant recorded under a blank config would claim the run had no
  configuration.
- Everything the gate refuses, unchanged: an unreproducible run, a winner
  outside its field, a duplicated variant.

## Does not

- Read a clock, shell out to git, or open a store. `as_of_ns`, `code` and
  `dataset` are the caller's — REQ-REPRO-001's FR-013, which this feature
  inherits rather than restates.
- Change what `publish` or `Registry` do.
