"""Every offered pane names a feature that exists (REQ-WP-030).

PRD §27.3's pane list lives in the web app and the feature registry lives here.
A pane naming a feature nobody registers renders "no readings of this feature"
forever -- a message the application produces honestly for a real absence -- so
a reader cannot tell a typo from a quiet market.

This is the only place the two lists meet. A check on either side alone would be
comparing a list against itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from channelflow.features import exposed_feature_names

PANES = Path(__file__).resolve().parents[3] / "apps" / "web" / "src" / "panes.ts"


class PaneListUnreadable(AssertionError):
    """The pane list could not be read, so the check below would prove nothing."""


def parse_panes(source: str) -> list[str]:
    """The features a pane list offers.

    Separate from reading the file so the parser itself can be tested: if the
    application's declaration ever changes shape, this returns nothing, every
    assertion below passes over an empty list, and the check silently stops
    checking. The mutation sweep found exactly that -- deleting the guard changed
    no result, because no test ever handed it a source it could not read.
    """
    block = re.search(r"export const PANES[^=]*=\s*\[(.*?)\];", source, re.S)
    if block is None:
        raise PaneListUnreadable("the source no longer declares PANES as a list")
    found = re.findall(r'feature:\s*"([^"]+)"', block.group(1))
    if not found:
        raise PaneListUnreadable("no panes were parsed; the check would pass vacuously")
    return found


def offered_features() -> list[str]:
    """The features the application's own pane list offers.

    Read from the module the application imports, never from a copy: a copy
    would agree with itself forever, which is the failure this test exists to
    prevent one level up.
    """
    return parse_panes(PANES.read_text())


@pytest.mark.trace("REQ-WP-030")
def test_every_offered_pane_names_a_registered_feature() -> None:
    registered = set(exposed_feature_names())

    unknown = [name for name in offered_features() if name not in registered]

    assert unknown == [], (
        f"pane(s) naming unregistered feature(s): {unknown}. A pane whose feature "
        "nobody registers shows 'no readings of this feature' forever, and reads "
        "as a quiet market rather than as a typo"
    )


@pytest.mark.trace("REQ-WP-030")
def test_the_derivatives_panes_are_offered() -> None:
    """Phase 3's own deliverable. REQ-WP-027 deferred these four in writing."""
    offered = set(offered_features())

    assert {"open_interest_usd", "funding_z", "basis_bps", "liquidation_imbalance_5m"} <= offered


@pytest.mark.trace("REQ-WP-030")
def test_the_order_flow_panes_are_still_offered() -> None:
    offered = set(offered_features())

    assert {"cvd", "ofi_1m", "depth_imbalance_10"} <= offered


@pytest.mark.trace("REQ-WP-030")
def test_the_dex_panes_are_not_offered_yet() -> None:
    """Phase 4's data is unfinished, and the reason REQ-WP-027 gave for deferring
    the derivatives panes applies unchanged to these."""
    offered = " ".join(offered_features())

    assert "swap_imbalance" not in offered
    assert "dex_" not in offered


@pytest.mark.trace("REQ-WP-030")
def test_a_pane_list_it_cannot_read_is_a_failure_not_an_empty_answer() -> None:
    """The guard that keeps this file from quietly stopping.

    A parser that returned nothing on an unfamiliar shape would make every
    assertion above pass over an empty list, and the check would go on being
    green while checking nothing at all.
    """
    with pytest.raises(PaneListUnreadable, match="no longer declares"):
        parse_panes("const SOMETHING_ELSE = [];")

    with pytest.raises(PaneListUnreadable, match="vacuously"):
        parse_panes("export const PANES: readonly Pane[] = [];")
