# @trace: REQ-INFRA-007
"""Where the signing key may be, and where it may not (FR-015, SC-008).

The worker is a long-running data pipeline that reads the network; the notary is one small process
that signs. Only the second is given the keystore, and nothing in any tracked file carries a key.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
SERVICES: dict[str, Any] = COMPOSE["services"]
KEY_SHAPE = re.compile(r"(0x)?[0-9a-fA-F]{64}")
KEY_NAMES = re.compile(r"PRIVATE_KEY|MNEMONIC|SECRET_KEY|KEYSTORE_PASSWORD|DEPLOYER_KEY", re.I)


def environment(service: str) -> dict[str, str]:
    env = SERVICES[service].get("environment", {})
    if isinstance(env, list):
        env = dict(item.split("=", 1) for item in env)
    return {k: str(v) for k, v in env.items()}


@pytest.mark.trace("REQ-INFRA-007")
def test_there_is_a_notary_service_that_starts_only_when_asked_for() -> None:
    notary = SERVICES["notary"]
    assert notary["command"][-1] == "channelflow.notary.main"
    assert (
        "notary" in notary["profiles"]
    )  # a plain `up` on a stack without keys must not crash-loop
    assert notary["restart"] == "unless-stopped"


@pytest.mark.trace("REQ-INFRA-007")
def test_only_the_notary_is_given_the_keystore_and_its_password() -> None:
    assert SERVICES["notary"]["secrets"] == ["notary_keystore", "notary_password"]
    for name, service in SERVICES.items():
        if name != "notary":
            assert "secrets" not in service, f"{name} must not mount a notary secret"
    for name, spec in COMPOSE["secrets"].items():
        assert "${" in spec["file"], f"{name} must be named by variable, not by a literal path"


@pytest.mark.trace("REQ-INFRA-007")
def test_the_worker_holds_no_key_and_no_chain_setting() -> None:
    names = set(environment("worker"))
    assert not {n for n in names if n.startswith("MONAD_") or "KEYSTORE" in n}, names
    assert {"CHANNELFLOW_NOTARY_ENABLED", "CHANNELFLOW_NOTARY_FROM"} <= names


@pytest.mark.trace("REQ-INFRA-007")
def test_no_environment_value_in_the_compose_file_is_or_names_a_key() -> None:
    for name in SERVICES:
        for key, value in environment(name).items():
            assert not KEY_NAMES.search(key), f"{name}.{key}"
            assert not KEY_SHAPE.fullmatch(value), f"{name}.{key} carries a key-shaped value"


@pytest.mark.trace("REQ-INFRA-007")
def test_the_commit_is_baked_in_at_build_for_the_worker_and_the_notary() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert (
        "ARG CHANNELFLOW_CODE_COMMIT" in dockerfile and "ARG CHANNELFLOW_CODE_DIRTY" in dockerfile
    )
    assert re.search(r"^ENV .*CHANNELFLOW_CODE_COMMIT", dockerfile, re.M)
    for name in ("worker", "notary"):
        args = SERVICES[name]["build"]["args"]
        assert {"CHANNELFLOW_CODE_COMMIT", "CHANNELFLOW_CODE_DIRTY"} <= set(args), name


@pytest.mark.trace("REQ-INFRA-007")
def test_the_build_info_target_prints_the_commit_and_the_dirty_flag_but_never_the_epoch() -> None:
    """The epoch is set once, in `.env`. Printed here, an exported value overrides `.env` on every
    deploy and moves the epoch forward -- which happened on 2026-10-08 and left a hole."""
    makefile = (ROOT / "Makefile").read_text()
    target = makefile.split("notary-build-info:")[1].split("\n\n")[0]
    for needle in ("CHANNELFLOW_CODE_COMMIT", "CHANNELFLOW_CODE_DIRTY"):
        assert needle in target
    assert "export CHANNELFLOW_NOTARY_FROM" not in target
    assert "git rev-parse HEAD" in target and "git status --porcelain" in target
