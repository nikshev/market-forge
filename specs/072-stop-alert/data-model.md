# Phase 1 — Data model

## `Notification` (protocol)

```python
notification_id: uuid.UUID
symbol: str
def render(self) -> str
def link(self) -> str
```

What the dispatcher needs and nothing more. `Alert` satisfies it; so does
`StopUpdateAlert`.

## `StopUpdateAlert`

```python
position: PositionState
proposal: StopProposal
stop_in_force: Decimal          # what the exchange was obeying
market_price: Decimal
event_time_ns: int
chart_base_url: str
```

`stop_in_force` is carried, not derived. Deriving it would mean the notification
re-deciding what was active, which is the replay's answer to give.

Derived readings:

| | Meaning |
|---|---|
| `open_risk_before_r` | entry against `stop_in_force`, over `R0` |
| `open_risk_after_r` | entry against the proposal, over `R0` |
| `moved` | the proposal's own answer |

Both risk figures floor at zero: a stop past entry has no open risk left, and
zero there is a reading rather than an absence.

## Rendering

§44A.34's blocks, in its order. An absent anchor omits the anchor block
([[ADR-016]]); reasons are rendered verbatim, including codes this build has
never seen.

## `StopUpdateGate`

```python
dispatcher: Dispatcher
debug: bool = False
```

`offer(alert, *, at_ns)` delivers a move; suppresses a hold or refusal with the
reason, unless `debug`, in which case it announces it as a hold.
