# Implementation Plan: A fitted model is registered, hashed and citable

**Branch**: `wp-022-model-registry` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

`artifact_hash(model)` over the model's whole dataclass state, a `Registration`
carrying PRD §23.9's eleven fields, a `ModelRegistry` on the canonical plane,
and `require_registered` so a run cannot cite a hash nobody holds.

The `Model` protocol gains one member, `fitted`. Only the model can answer:
`LogisticRegression` holds `None` weights, `GradientBoostedTrees` holds an empty
tree list, `GMDHNetwork` holds an absent search result, and there is no test from
outside that covers all three.

## Technical Context

**Language/Version**: Python 3.12 · **Dependencies**: none new · **Storage**: a new lakehouse table

**Testing**: pytest with `@pytest.mark.trace("REQ-WP-022")`, plus a mutation sweep over the hashing internals.

**Constraints**: exact bytes; framed like [[REQ-REPRO-001]]'s run hash; a stored hash is read, never recomputed.

**Scale/Scope**: one new module, one protocol member across four models and two stand-ins, one table.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **XI. Results are reproducible** | This is the fourth of §0.13's four hashes and the last with no producer. | **Pass, and it is the point.** |
| **III. History is immutable** | Registrations go on the append-only plane. | **Pass**, with [[ADR-056]]'s watermark: an artifact already held is not written again. |
| **VI. Every feature is documented** | Eleven fields, none defaulted. | **Pass.** |
| **IX. Deterministic in backtest mode** | The hash is exact bytes, so it is stable for a given platform and honest across platforms. | **Pass**, and the limit is stated rather than hidden. |

No violations.

## Project Structure

```text
src/channelflow/models/registry.py   # NEW: artifact_hash, Registration, ModelRegistry, require_registered
src/channelflow/models/base.py       # Model protocol gains `fitted`; LogisticRegression implements it
src/channelflow/models/{regularized,boosting,gmdh}.py   # the other three
src/channelflow/research/gmdh_extrema.py   # _Named answers False
src/channelflow/turning/experiment.py      # _PredictionSource answers False
tests/unit/models/test_registry.py   # NEW
```

**Structure Decision**: the registry lives with the models rather than in
`experiments/`, because an artifact hash is a property of a model and the
experiment registry is its consumer, not its owner.
