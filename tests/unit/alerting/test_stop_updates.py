"""A stop update is announced with the risk it changed (REQ-WP-034).

PRD §44A.34's message, in which every line is a transition.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from channelflow.alerting import Dispatcher, StopUpdateAlert, StopUpdateGate
from channelflow.stops import (
    AnchorKind,
    PositionPhase,
    PositionState,
    ReasonCode,
    StopAnchor,
    StopProposal,
)

BASE_NS = 1788838800000000000
POSITION_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


class Recording:
    """A transport that records rather than sends."""

    def __init__(self, response: str = "ok") -> None:
        self.sent: list[tuple[str, str]] = []
        self.response = response

    def send(self, text: str, *, link: str) -> str:
        self.sent.append((text, link))
        return self.response


class Throwing:
    def send(self, text: str, *, link: str) -> str:
        raise RuntimeError("the network is a place where things go wrong")


def position(**overrides: object) -> PositionState:
    """Entry 112,400, initial stop 111,180. R0 = 1,220 -- §44A.34's own numbers."""
    fields: dict[str, object] = {
        "position_id": POSITION_ID,
        "instrument_id": "BTCUSDT",
        "venue": "binance",
        "side": "LONG",
        "quantity": Decimal("1"),
        "entry_time_ns": BASE_NS,
        "average_entry_price": Decimal("112400"),
        "initial_stop_price": Decimal("111180"),
        "current_strategy_stop": Decimal("111180"),
    }
    fields.update(overrides)
    return PositionState(**fields)  # type: ignore[arg-type]


def proposal(
    *,
    price: str = "112060",
    reasons: tuple[ReasonCode, ...] = (ReasonCode.STRUCTURAL_ANCHOR,),
    anchored: bool = True,
) -> StopProposal:
    return StopProposal(
        price=Decimal(price),
        anchor=StopAnchor(
            kind=AnchorKind.CONFIRMED_SWING,
            price=Decimal(price),
            known_at_ns=BASE_NS,
            description="confirmed higher low",
        )
        if anchored
        else None,
        reasons=reasons,
        at_ns=BASE_NS + 60_000_000_000,
        phase=PositionPhase.STRUCTURE_TRAIL,
    )


def alert(**overrides: object) -> StopUpdateAlert:
    fields: dict[str, object] = {
        "position": position(),
        "proposal": proposal(),
        "stop_in_force": Decimal("111180"),
        "market_price": Decimal("113740"),
        "event_time_ns": BASE_NS + 60_000_000_000,
        "chart_base_url": "https://charts.example",
    }
    fields.update(overrides)
    return StopUpdateAlert(**fields)  # type: ignore[arg-type]


def gate(debug: bool = False) -> tuple[StopUpdateGate, Recording, Dispatcher]:
    transport = Recording()
    dispatcher = Dispatcher(transport=transport)
    return StopUpdateGate(dispatcher=dispatcher, debug=debug), transport, dispatcher


# --- the message is the difference -------------------------------------------


@pytest.mark.trace("REQ-WP-034")
def test_the_message_states_both_stops() -> None:
    """A message saying only where the stop now sits reports what the chart
    already shows and withholds the one thing it does not.

    Asserted as a pair on purpose: an assertion on the new stop alone passes for
    a renderer that lost the "from" half, and the message would still look
    complete.
    """
    text = alert().render()

    assert "111,180" in text
    assert "112,060" in text


@pytest.mark.trace("REQ-WP-034")
def test_the_message_states_the_risk_before_and_after() -> None:
    """§44A.34: `Open risk: 1.00R -> 0.28R`.

    Entry 112,400, R0 = 1,220. In force at 111,180 that is the full 1.00R; moved
    to 112,060 it is 340/1220 = 0.28R.
    """
    text = alert().render()

    assert "1.00R -> 0.28R" in text


@pytest.mark.trace("REQ-WP-034")
def test_the_old_stop_is_the_one_that_was_in_force() -> None:
    """REQ-WP-033's distinction, arriving here.

    A move decided while an earlier update was still in flight must announce the
    stop the exchange was obeying. Announcing the last decided level describes a
    change that did not happen, in a message whose only job is to say what
    changed.
    """
    # The position's own `current_strategy_stop` is the level last decided;
    # 111,180 is what the exchange had actually acknowledged.
    stale = position(current_strategy_stop=Decimal("111600"))

    text = alert(position=stale, stop_in_force=Decimal("111180")).render()

    assert "111,180" in text
    assert "111,600" not in text
    # And the risk figure reads from the same stop. Asserted separately because
    # the level and the risk are two renderings of one fact, and the mutation
    # sweep showed they can disagree: reading the position's last decided stop
    # here gives 0.66R -> 0.28R, a smaller move from a level never in force,
    # while the "Old stop" line above still says 111,180.
    assert "1.00R -> 0.28R" in text


@pytest.mark.trace("REQ-WP-034")
def test_open_risk_floors_at_zero_once_the_stop_passes_entry() -> None:
    """Zero here is a reading: there is no open risk left. Not an absence."""
    beyond = alert(proposal=proposal(price="113000"))

    assert beyond.open_risk_after_r == 0.0


@pytest.mark.trace("REQ-WP-034")
def test_the_anchor_and_the_reasons_reach_the_message() -> None:
    text = alert().render()

    assert "confirmed higher low" in text
    assert ReasonCode.STRUCTURAL_ANCHOR.value in text


@pytest.mark.trace("REQ-WP-034")
def test_a_proposal_with_no_anchor_omits_the_block() -> None:
    """ADR-016: absent, never dashed. A dash where a value sits in every other
    message is a formatting difference, not an absence."""
    text = alert(proposal=proposal(anchored=False)).render()

    assert "Anchor" not in text


@pytest.mark.trace("REQ-WP-034")
def test_the_message_carries_a_reason_nobody_taught_it() -> None:
    """A dropped reason is a veto that reads as no veto."""
    text = alert(
        proposal=proposal(reasons=(ReasonCode.STRUCTURAL_ANCHOR, ReasonCode.NOISE_BUFFER_APPLIED))
    ).render()

    assert ReasonCode.NOISE_BUFFER_APPLIED.value in text


# --- holds do not ring the phone ---------------------------------------------


@pytest.mark.trace("REQ-WP-034")
def test_a_hold_is_not_announced() -> None:
    """Stop policies hold far more often than they move. A channel reporting
    every held micro-adjustment trains its reader to ignore it, at which point
    the alerts that matter are lost exactly as silence would lose them."""
    held, transport, dispatcher = gate(debug=False)

    record = held.offer(
        alert(proposal=proposal(reasons=(ReasonCode.HELD_COOLDOWN,))), at_ns=BASE_NS
    )

    assert transport.sent == []
    assert record.status == "suppressed"


@pytest.mark.trace("REQ-WP-034")
def test_a_suppression_is_recorded_rather_than_silent() -> None:
    """A suppression that leaves no trace is indistinguishable from there having
    been nothing to say."""
    held, _, dispatcher = gate(debug=False)

    held.offer(alert(proposal=proposal(reasons=(ReasonCode.HELD_NO_ANCHOR,))), at_ns=BASE_NS)

    assert len(dispatcher.audit) == 1
    assert ReasonCode.HELD_NO_ANCHOR.name in dispatcher.audit[0].reason


@pytest.mark.trace("REQ-WP-034")
def test_a_refusal_is_not_announced_either() -> None:
    held, transport, _ = gate(debug=False)

    held.offer(alert(proposal=proposal(reasons=(ReasonCode.REFUSED_BEYOND_MARKET,))), at_ns=BASE_NS)

    assert transport.sent == []


@pytest.mark.trace("REQ-WP-034")
def test_a_move_is_announced() -> None:
    moving, transport, _ = gate(debug=False)

    record = moving.offer(alert(), at_ns=BASE_NS)

    assert record.status == "delivered"
    assert len(transport.sent) == 1


@pytest.mark.trace("REQ-WP-034")
def test_debug_announces_a_hold_as_a_hold() -> None:
    """ "STOP UPDATED" above a stop that did not move is a false sentence, in the
    one mode a reader turns on because they distrust what is happening."""
    debugging, transport, _ = gate(debug=True)

    debugging.offer(alert(proposal=proposal(reasons=(ReasonCode.HELD_COOLDOWN,))), at_ns=BASE_NS)

    text = transport.sent[0][0]
    assert "STOP UPDATED" not in text
    assert "STOP HELD" in text


@pytest.mark.trace("REQ-WP-034")
def test_debug_does_not_invent_events() -> None:
    """It widens what is announced; it does not manufacture anything."""
    debugging, transport, _ = gate(debug=True)

    debugging.offer(alert(), at_ns=BASE_NS)

    assert len(transport.sent) == 1


# --- one dispatcher, one audit -----------------------------------------------


@pytest.mark.trace("REQ-WP-034")
def test_delivery_retries_and_dead_letters_like_a_signal_alert() -> None:
    dispatcher = Dispatcher(transport=Recording(response="nope"), max_attempts=3)

    record = dispatcher.deliver(alert(), at_ns=BASE_NS)

    assert record.status == "dead_lettered"
    assert len(record.attempts) == 3


@pytest.mark.trace("REQ-WP-034")
def test_a_throwing_transport_never_escapes_into_the_caller() -> None:
    """ADR-018. An exception travelling back into the engine is the blocking
    this exists to prevent, wearing a different shape."""
    dispatcher = Dispatcher(transport=Throwing(), max_attempts=1)

    record = dispatcher.deliver(alert(), at_ns=BASE_NS)

    assert record.status == "dead_lettered"
    assert "RuntimeError" in record.attempts[0].detail


@pytest.mark.trace("REQ-WP-034")
def test_the_audit_names_the_instrument() -> None:
    dispatcher = Dispatcher(transport=Recording())

    record = dispatcher.deliver(alert(), at_ns=BASE_NS)

    assert record.symbol == "BTCUSDT"


@pytest.mark.trace("REQ-WP-034")
def test_the_notification_id_is_derived_rather_than_generated() -> None:
    """ADR-017. A generated id makes a replay produce different notifications,
    different dedupe decisions and a different audit -- all looking correct."""
    assert alert().notification_id == alert().notification_id
    assert alert().notification_id != alert(proposal=proposal(price="112500")).notification_id


@pytest.mark.trace("REQ-WP-034")
def test_the_link_carries_the_alert_s_own_host() -> None:
    """A hard-coded host works in exactly one deployment."""
    assert alert().link().startswith("https://charts.example/")
