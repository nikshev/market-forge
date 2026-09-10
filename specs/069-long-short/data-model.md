# Phase 1 — Data model

## `DerivativesState` — two new fields

```python
long_short_ratio: float | None = Field(default=None, gt=0.0)
top_trader_long_short_ratio: float | None = Field(default=None, gt=0.0)
```

`None` is the default and means **nobody published**. It is not a placeholder
for a value that will arrive; it is the answer when the venue is silent.

`gt=0.0` refuses zero and below at construction. A ratio of zero says there are
no longs at all, which no venue reports and which breaks every ratio built on
it. Refusing at the boundary keeps the check in one place rather than in each
reader.

Nothing else on the state changes. The golden fixture regenerated to exactly two
added `null` keys, with no existing value touched — which is what the fixture
guard exists to show.

## Readings

| Reading | Returns | When it refuses |
|---|---|---|
| `long_short_ratio` | `float \| None` | no state; the state is stale |
| `top_trader_ratio` | `float \| None` | the same |
| `long_short_z` | `ZScore` | fewer readings than the window; the newest reading is stale |
| `top_trader_z` | `ZScore` | the same |

The first two return `None` for "nobody published" and raise for "nothing to
read". Those are different failures: a silent venue that is answering, versus no
answer at all.

## State transitions

None. Every reading is a pure function of a state list and the instant asked
about.
