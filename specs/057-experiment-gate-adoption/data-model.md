# Phase 1 — Data model

Two new value objects and one protocol. No table, no schema change: the registry
row is [[REQ-REPRO-001]]'s and is not touched.

## `Field`

What one comparison compared.

| Field | Type | Rule |
|---|---|---|
| `variants` | `Mapping[str, Mapping[str, ConfigValue]]` | variant name → the configuration that distinguishes it. Non-empty. |
| `chosen` | `str \| None` | the variant this comparison chose, or `None` for a comparison that deliberately chooses none. |

**Validation**

- `variants` must be non-empty. A comparison of nothing is not a comparison, and
  a field of zero would pass the gate vacuously.
- `chosen`, when present, must be a key of `variants`. The gate refuses a winner
  outside its own field; catching it here means the comparison cannot construct
  the refusal in the first place.
- Duplicate names cannot arise: a mapping has one entry per key. This is why the
  field is a mapping rather than a sequence of pairs — the gate's
  duplicate-variant refusal stays as the backstop for a caller assembling a field
  by hand, and becomes unreachable from a comparison.

**Deliberately absent**: any metric. A field says what was compared and what was
picked, never how well anything did. Metrics stay in each comparison's own
report, where a reader can disagree with a definition.

## `Compared` (protocol)

One member: `field -> Field`. Every comparison type produced by the research
package satisfies it. Runtime-checkable, because the discovered check in
FR-012 tests types it has never heard of.

## `config_of(obj)` (helper)

`{"variant": type(obj).__name__} | dataclasses.asdict(obj)` for a dataclass
variant. The type name is included because two dataclasses can carry identical
fields and mean different things — `Method.KALMAN` and a Kalman channel share
nothing but would not be distinguished by fields alone in every case.

Raises rather than returns a partial config when the object is not a dataclass
and the module has given no explicit config: a variant recorded under an empty
configuration would say the run had none.

## Module declarations

Each research module declares two module-level constants:

| Name | Type | Meaning |
|---|---|---|
| `EXPERIMENT` | `str` | which experiment this module is. Not a requirement id: `ablation` belongs to `REQ-US-006`/`-007` and still compares arms. |
| `COMPARISON` | `type` | the comparison type its entry point returns, which must satisfy `Compared`. |

These are what makes FR-012 discoverable. Two modules may name the same
`COMPARISON` type (`cumulative` and `ofi_incremental` both return
`IncrementalReport`) and must not name the same `EXPERIMENT`.
