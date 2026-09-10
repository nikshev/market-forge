# Contract — the artifact hash and the registry

```
artifact_hash(model) -> str          # refuses an unfitted model
ModelRegistry.record(entries)        # skips artifacts already held
ModelRegistry.entries() -> tuple[Registration, ...]
ModelRegistry.holds(artifact) -> bool
require_registered(identity, *, models)   # refuses an unresolvable hash
```

## Guarantees

- identical fits hash identically; any difference in state or hyperparameters changes the hash;
- an unfitted model raises rather than returning a string every unfitted model of its type would share;
- a stored registration reads back field for field, its hash **read** and not recomputed;
- a run whose `model_artifact` is `NO_MODEL` or `UNRECORDED` needs no registration;
- a run citing a hash no registration carries is refused, naming it.

## Does not

Load a model, promote one, or decide deployment. `deployment_status` records
what was decided; deciding belongs to [[REQ-EXP-008]] and the gate.
