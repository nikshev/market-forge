"""The gap threshold, as configuration (REQ-WP-087, Principle X).

PRD Principle X: a threshold is configuration, not a compiled-in constant. This one
decides how large a hole in the bar series makes the extremum detector and the channel
fit restart at it -- so the number must be readable from the environment, default to one
missing bar, and refuse what no hole could ever mean.
"""

# @trace: REQ-WP-087

from __future__ import annotations

import pytest

from channelflow.settings import MissingConfiguration, settings_from_env

BASE = {"CHANNELFLOW_CATALOG_URI": "sqlite:///x.db", "CHANNELFLOW_WAREHOUSE": "/tmp/w"}

VARIABLE = "CHANNELFLOW_GAP_THRESHOLD"


@pytest.mark.trace("REQ-WP-087")
def test_a_deployment_that_sets_nothing_gets_one_missing_bar() -> None:
    """The documented default: bridge a single missing bar, restart on two or more."""
    assert settings_from_env(BASE).gap_threshold == 1


@pytest.mark.trace("REQ-WP-087")
def test_a_blank_threshold_is_the_default_not_a_parse_failure() -> None:
    """Compose forwards `${CHANNELFLOW_GAP_THRESHOLD:-}`; blank counts as absent here,
    as it does for every other variable read by `settings_from_env`."""
    assert settings_from_env({**BASE, VARIABLE: ""}).gap_threshold == 1


@pytest.mark.trace("REQ-WP-087")
@pytest.mark.parametrize(("text", "threshold"), [("0", 0), ("1", 1), ("3", 3)])
def test_the_threshold_is_a_whole_number_of_missing_bars(text: str, threshold: int) -> None:
    assert settings_from_env({**BASE, VARIABLE: text}).gap_threshold == threshold


@pytest.mark.trace("REQ-WP-087")
def test_zero_is_a_threshold_not_a_mistake() -> None:
    """0 means any gap restarts the models. It reads like an unset value and is not one:
    refusing it would leave no way to say "restart on any gap"."""
    assert settings_from_env({**BASE, VARIABLE: "0"}).gap_threshold == 0


@pytest.mark.trace("REQ-WP-087")
@pytest.mark.parametrize("text", ["-1", "-148"])
def test_a_negative_threshold_is_refused_naming_the_variable(text: str) -> None:
    """No hole is smaller than zero, so a negative count names nothing -- and it must not
    be read as `0`'s sibling, since the sign is the whole difference between them."""
    with pytest.raises(MissingConfiguration, match=VARIABLE):
        settings_from_env({**BASE, VARIABLE: text})


@pytest.mark.trace("REQ-WP-087")
@pytest.mark.parametrize("text", ["abc", "1.5", "1_0", "two"])
def test_something_that_is_not_a_whole_number_is_refused(text: str) -> None:
    with pytest.raises(MissingConfiguration, match=VARIABLE):
        settings_from_env({**BASE, VARIABLE: text})
