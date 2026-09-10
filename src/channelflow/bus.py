"""One place events go, and one place consumers listen.

# @trace: REQ-INFRA-003

PRD §45's Phase 0 asks for an "event bus abstraction" and says nothing else
about it anywhere, so this is written from the cost the wiring actually has.

`BarBuilder(on_final=…)` and `BacktestRunner(on_snapshot=…, on_candidate=…)`
require a producer to be told its consumer at construction. That works, and it
means **a producer cannot be observed by anyone it was not built with**: a
second consumer of finalized bars is a change at the builder's construction
site, and a third is another. With a bus each producer takes one publishing hook
and every consumer subscribes.

**Synchronous, and in subscription order.** Principle XI requires a replay to
reproduce a result exactly. A bus that dispatched concurrently or reordered
would break that at the foundation while looking like plumbing, and the failure
would surface far from its cause -- so it is in [[REQ-INFRA-003]]'s acceptance
rather than left here as an implementation note.

**A handler's exception propagates.** Catching so one bad handler cannot stop
the rest sounds robust and buries the failure at the layer with least context
about it. In a replay a swallowed handler is a missing row nobody hears about,
and the canonical plane's whole claim is that what is recorded is what happened.

There is no unsubscribe, no buffering, no retry and no persistence. Each is a
real feature and none has a caller; [[ADR-002]]'s plane is where durability
lives.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

E = TypeVar("E")


@dataclass
class EventBus:
    """Subscriptions by exact event type, delivered in the order they were made."""

    #: Exact type to its handlers. Exact, not by inheritance: walking the MRO on
    #: every publish would answer "does a subscriber to a base class see
    #: subclasses?", which is a real question nobody here is asking. Adding it
    #: later is easy; removing it once something depends on it is not.
    _handlers: dict[type, list[Callable[..., None]]] = field(default_factory=dict)

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Register `handler` for events of exactly `event_type`.

        The same handler twice is two subscriptions and is called twice. A bus
        that deduplicated would make a caller's double registration invisible,
        and a double registration is a bug worth seeing rather than absorbing.
        """
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: object) -> None:
        """Deliver `event` to its subscribers, in order.

        Over a copy of the list, because a handler may subscribe another one --
        and iterating the live list would make that either a `RuntimeError` or a
        silently skipped handler depending on which way it mutated. Neither is a
        behaviour anyone would choose; both are what you get by not choosing.
        The copy also fixes the meaning: a subscription made during a dispatch
        starts at the next event.
        """
        for handler in list(self._handlers.get(type(event), ())):
            handler(event)
