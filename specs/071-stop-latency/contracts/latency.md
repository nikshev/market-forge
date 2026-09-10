# Contract — activation latency

```python
ActivationLatency(decision_ns=0, computation_ns=0, exchange_ns=160_000_000)
ActivationLatency.none()
Replay(costs=..., latency=...)
```

## Guarantees

- A stop decided at `t` is never active before `t + total_ns`, and is not active
  at exactly `t + total_ns` — the predeclared conservative tie.
- Triggers are evaluated against the active stop; the policy is shown the
  decided one.
- Every policy in one comparison, baselines included, runs under one latency.
- `ActivationLatency.none()` reproduces the outcomes recorded before this
  feature, field for field.
- The default is non-zero and traceable to §44A.27's example; its total is a
  floor, because two of its three legs have no published figure.
- A report states the latency it was produced under.
- `stop_updates` counts decisions; `stop_updates_activated` counts the ones
  obeyed inside the path.

## Does not

Model partial fills, acknowledgement failures, or a rejected modification. A
stop update that the exchange refuses is a different fact from one that arrives
late, and nothing here pretends to cover it.
