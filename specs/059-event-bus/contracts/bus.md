# Contract — the bus

```
subscribe(event_type: type[E], handler: Callable[[E], None]) -> None
publish(event: object) -> None
```

## Guarantees

- Handlers for the event's **exact** type, in subscription order, synchronously.
- A handler subscribed twice is called twice.
- A subscription made during a dispatch does not receive that dispatch.
- An event with no subscribers is a no-op.
- A handler's exception propagates to the publisher.

## Not offered

Unsubscribe, buffering, retry, persistence, concurrency, inheritance dispatch,
or delivery to a subscriber added for a base class. Each is a real feature and
none has a caller; [[ADR-002]]'s plane is where durability lives.
