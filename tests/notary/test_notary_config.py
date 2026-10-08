# @trace: REQ-INFRA-007
"""The worker's notary configuration: off by default, explicit when on (FR-016)."""

from __future__ import annotations

import pytest

from channelflow.notary.config import ConfigError, worker_notary_from_env

COMMIT = "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.trace("REQ-INFRA-007")
def test_the_notary_is_off_unless_it_is_switched_on() -> None:
    assert worker_notary_from_env({}) is None
    assert worker_notary_from_env({"CHANNELFLOW_NOTARY_ENABLED": "false"}) is None
    assert worker_notary_from_env({"CHANNELFLOW_NOTARY_ENABLED": ""}) is None


@pytest.mark.trace("REQ-INFRA-007")
def test_switched_on_it_needs_an_explicit_epoch() -> None:
    with pytest.raises(ConfigError, match="CHANNELFLOW_NOTARY_FROM"):
        worker_notary_from_env({"CHANNELFLOW_NOTARY_ENABLED": "true"})
    with pytest.raises(ConfigError, match="CHANNELFLOW_NOTARY_FROM"):
        worker_notary_from_env(
            {"CHANNELFLOW_NOTARY_ENABLED": "true", "CHANNELFLOW_NOTARY_FROM": "yesterday-ish"}
        )


@pytest.mark.trace("REQ-INFRA-007")
def test_the_epoch_is_an_instant_and_the_commit_comes_from_the_build() -> None:
    config = worker_notary_from_env(
        {
            "CHANNELFLOW_NOTARY_ENABLED": "true",
            "CHANNELFLOW_NOTARY_FROM": "2026-10-08T12:00:00Z",
            "CHANNELFLOW_CODE_COMMIT": COMMIT,
            "CHANNELFLOW_CODE_DIRTY": "false",
        }
    )
    assert config is not None
    assert config.from_ns == 1_791_460_800_000_000_000
    assert (config.code_commit, config.code_dirty) == (COMMIT, "false")


@pytest.mark.trace("REQ-INFRA-007")
def test_an_unset_commit_is_carried_as_absent_not_defaulted() -> None:
    config = worker_notary_from_env(
        {"CHANNELFLOW_NOTARY_ENABLED": "1", "CHANNELFLOW_NOTARY_FROM": "2026-10-08T12:00:00+00:00"}
    )
    assert config is not None and config.code_commit is None and config.code_dirty is None
