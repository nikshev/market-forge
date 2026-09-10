# Phase 1 — Data model

Three event values and one registry. No persistence.

## Events

| Event | Carries | Published when |
|---|---|---|
| `BarFinalized` | `bar: Bar` | a window closes and cannot change |
| `ChannelFitted` | `bar: Bar`, `snapshot: ChannelSnapshot` | a channel is fitted on a bar |
| `CandidateUpdated` | `candidate: Candidate` | a signal's state advances |

Frozen values. `CandidateUpdated` is named for what it is: the machine emits the
same signal repeatedly, each time more complete, and a name like `SignalOpened`
would say something the event does not mean — the distinction
[[REQ-PIPE-001]] already had to make in its recorder.

## `EventBus`

| Member | Rule |
|---|---|
| `subscribe(event_type, handler)` | appends; the same handler twice is two subscriptions |
| `publish(event)` | delivers to the exact type's subscribers, in order, over a copy of the list |

No unsubscribe. Nothing needs one, and a bus whose subscriptions can disappear
mid-run is a harder thing to reason about in a replay than one whose cannot.
