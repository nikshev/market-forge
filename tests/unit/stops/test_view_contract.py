"""The wire shapes the position view reads match the models (REQ-WP-032).

PRD §44A.33's view is TypeScript and PRD §44A's stop engine is Python. Nothing
serves the path yet, so today the two ends agree because one person wrote both.
The moment a field is added to `StopProposal`, they stop agreeing, and the way
that failure shows up is the one this requirement is about: the view keeps
rendering, correctly, a decision that is missing a reason it never heard of.

This is the only place the two declarations meet. Checking either side alone
compares a list against itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from channelflow.stops import PositionState, ReasonCode, StopAnchor, StopProposal

TYPES = Path(__file__).resolve().parents[3] / "apps" / "web" / "src" / "types.ts"


class InterfaceUnreadable(AssertionError):
    """The interface could not be read, so the check below would prove nothing."""


def parse_interface(source: str, name: str) -> set[str]:
    """The field names one TypeScript interface declares.

    Separate from reading the file so the parser itself can be tested. A parser
    that returns nothing when the source changes shape turns every assertion
    below into a comparison against an empty set, and the check goes on being
    green while checking nothing -- the failure the pane check's sweep found.
    """
    block = re.search(rf"export interface {name} \{{(.*?)\n\}}", source, re.S)
    if block is None:
        raise InterfaceUnreadable(f"the source no longer declares an interface named {name}")
    fields = set(re.findall(r"^\s{2}(\w+)\??:", block.group(1), re.M))
    if not fields:
        raise InterfaceUnreadable(f"no fields were parsed from {name}; the check is vacuous")
    return fields


@pytest.fixture(scope="module")
def source() -> str:
    return TYPES.read_text()


@pytest.mark.trace("REQ-WP-032")
def test_a_source_that_declares_no_such_interface_is_a_failure() -> None:
    with pytest.raises(InterfaceUnreadable):
        parse_interface("export const PANES = [];", "StopProposalOut")


@pytest.mark.trace("REQ-WP-032")
def test_an_interface_with_no_fields_is_a_failure() -> None:
    """Not an empty answer: an empty answer passes every assertion below."""
    with pytest.raises(InterfaceUnreadable):
        parse_interface("export interface StopProposalOut {\n}", "StopProposalOut")


@pytest.mark.trace("REQ-WP-032")
def test_every_anchor_field_reaches_the_view(source: str) -> None:
    """An anchor field the view never learns about is a level shown without the
    thing that justified it."""
    assert set(StopAnchor.model_fields) <= parse_interface(source, "StopAnchorOut")


@pytest.mark.trace("REQ-WP-032")
def test_every_proposal_field_reaches_the_view(source: str) -> None:
    """The drift this check exists for.

    A field added to `StopProposal` and not to the view produces no error and no
    gap: the view keeps drawing a decision, correctly, missing the part that was
    added because someone thought a reader needed it.
    """
    assert set(StopProposal.model_fields) <= parse_interface(source, "StopProposalOut")


@pytest.mark.trace("REQ-WP-032")
def test_the_view_invents_no_position_field(source: str) -> None:
    """The other direction. A view field with no model behind it is a value that
    can only ever be filled in by the view itself, which is where a plausible
    number comes from."""
    assert parse_interface(source, "PositionOut") <= set(PositionState.model_fields)


@pytest.mark.trace("REQ-WP-032")
def test_the_view_renders_moved_and_refused_because_both_can_happen(source: str) -> None:
    """`moved` and `refused` are the two flags the view derives rather than
    reads, and each needs something behind it.

    `moved` is `StopProposal`'s own property. `refused` is any `REFUSED_*`
    reason code -- and if the last of those were ever removed, the view would
    keep a whole rendering branch that nothing on earth could reach, which reads
    as coverage and is dead.
    """
    fields = parse_interface(source, "StopProposalOut")

    assert {"moved", "refused"} <= fields
    assert isinstance(StopProposal.moved, property)
    assert [r for r in ReasonCode if r.name.startswith("REFUSED")]
