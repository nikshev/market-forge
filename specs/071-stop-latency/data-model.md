# Phase 1 — Data model

## `ActivationLatency`

```python
@dataclass(frozen=True)
class ActivationLatency:
    decision_ns: int = 0
    computation_ns: int = 0
    exchange_ns: int = 160_000_000
    @property
    def total_ns(self) -> int
    @classmethod
    def none(cls) -> ActivationLatency
```

Three named legs because §44A.27 names three. Two of them default to zero
because the PRD gives them no figure, and the total therefore states a floor.
`none()` is the instantaneous case, expressible and never the default.

Negative legs are refused: a stop obeyed before it was decided is not a slow
exchange, it is a broken model.

## `Replay`

Gains `latency: ActivationLatency`. Inside a run, one variable becomes two:

| | Meaning | Used for |
|---|---|---|
| decided | what the policy has asked for | what the policy is shown next |
| active | what the exchange is obeying | triggers, and the distance the walk records |

A decision made at `t` joins a queue and becomes active at the first observation
strictly after `t + total_ns`.

## `StopPolicyOutcome`

Gains `stop_updates_activated: int = 0`. `stop_updates` keeps its meaning —
decisions made — so a report can say four were decided and one was obeyed, which
is the sentence the whole requirement exists to make sayable.

## `ComparisonReport`

Gains `latency: ActivationLatency`. Two reports produced under different
latencies are not comparable, and nothing about their shape says so.
