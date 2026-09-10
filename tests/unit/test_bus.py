"""One event bus between producers and consumers (REQ-INFRA-003)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from channelflow.bus import EventBus


@dataclass(frozen=True)
class Ping:
    value: int


@dataclass(frozen=True)
class Pong:
    value: int


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.mark.trace("REQ-INFRA-003")
def test_an_event_with_no_subscriber_is_published_without_effect(bus: EventBus) -> None:
    """The whole point of the abstraction: a producer publishes without knowing
    whether anyone is listening, so "nobody is" cannot be an error."""
    bus.publish(Ping(1))


@pytest.mark.trace("REQ-INFRA-003")
def test_every_subscriber_to_a_type_receives_the_event(bus: EventBus) -> None:
    """A second consumer is a subscription, not a change at the producer's
    construction site -- which is the cost this exists to remove."""
    first: list[int] = []
    second: list[int] = []
    bus.subscribe(Ping, lambda event: first.append(event.value))
    bus.subscribe(Ping, lambda event: second.append(event.value))

    bus.publish(Ping(7))

    assert first == [7]
    assert second == [7]


@pytest.mark.trace("REQ-INFRA-003")
def test_a_subscriber_to_another_type_receives_nothing(bus: EventBus) -> None:
    seen: list[object] = []
    bus.subscribe(Pong, seen.append)

    bus.publish(Ping(1))

    assert seen == []


@pytest.mark.trace("REQ-INFRA-003")
def test_subscribers_run_in_subscription_order(bus: EventBus) -> None:
    """Principle XI rests on this. A bus that reordered would break a replay's
    reproducibility while looking like plumbing, and the failure would surface
    a long way from its cause."""
    order: list[str] = []
    bus.subscribe(Ping, lambda _: order.append("first"))
    bus.subscribe(Ping, lambda _: order.append("second"))
    bus.subscribe(Ping, lambda _: order.append("third"))

    bus.publish(Ping(1))

    assert order == ["first", "second", "third"]


@pytest.mark.trace("REQ-INFRA-003")
def test_two_identical_runs_deliver_identical_sequences() -> None:
    """SC-004, stated over the bus rather than over a replay, because this is
    where the property either holds or does not."""

    def run() -> list[int]:
        seen: list[int] = []
        bus = EventBus()
        bus.subscribe(Ping, lambda event: seen.append(event.value))
        bus.subscribe(Pong, lambda event: seen.append(-event.value))
        for index in range(5):
            bus.publish(Ping(index))
            bus.publish(Pong(index))
        return seen

    assert run() == run()


@pytest.mark.trace("REQ-INFRA-003")
def test_the_same_handler_subscribed_twice_is_called_twice(bus: EventBus) -> None:
    """A bus that silently deduplicated would make a caller's double
    registration invisible -- and a double registration is a bug worth seeing,
    not one worth absorbing."""
    seen: list[int] = []

    def handler(event: Ping) -> None:
        seen.append(event.value)

    # The same object twice, deliberately. Two lambdas that happen to do the
    # same thing are two different objects, and a deduplicating bus would keep
    # both of them -- so a test written that way passes whether or not the
    # behaviour it names is there. This one found that out.
    bus.subscribe(Ping, handler)
    bus.subscribe(Ping, handler)

    bus.publish(Ping(3))

    assert seen == [3, 3]


@pytest.mark.trace("REQ-INFRA-003")
def test_a_subscription_made_during_dispatch_waits_for_the_next_event(
    bus: EventBus,
) -> None:
    """The obvious implementation iterates the live list, and mutating a list
    while iterating it is either a RuntimeError or a silently skipped handler.
    Neither is a behaviour anyone would choose; both are what you get by not
    choosing."""
    late: list[int] = []

    def subscribe_a_latecomer(_: Ping) -> None:
        bus.subscribe(Ping, lambda event: late.append(event.value))

    bus.subscribe(Ping, subscribe_a_latecomer)

    bus.publish(Ping(1))
    assert late == []

    bus.publish(Ping(2))
    assert late == [2]


@pytest.mark.trace("REQ-INFRA-003")
def test_a_subscribers_exception_reaches_the_publisher(bus: EventBus) -> None:
    """Catching so one bad handler cannot stop the rest sounds robust and buries
    the failure at the layer with least context about it. In a replay a
    swallowed handler is a missing row nobody hears about."""

    def raises(_: Ping) -> None:
        raise RuntimeError("this handler is broken")

    bus.subscribe(Ping, raises)

    with pytest.raises(RuntimeError, match="broken"):
        bus.publish(Ping(1))


@pytest.mark.trace("REQ-INFRA-003")
def test_dispatch_is_by_exact_type(bus: EventBus) -> None:
    """Subscribing to a base class and receiving subclasses is a real feature
    nobody is asking for. Adding it later is easy; removing it once someone
    depends on it is not."""

    @dataclass(frozen=True)
    class LoudPing(Ping):
        pass

    seen: list[object] = []
    bus.subscribe(Ping, seen.append)

    bus.publish(LoudPing(1))

    assert seen == []
