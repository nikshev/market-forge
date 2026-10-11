# @trace: REQ-INFRA-013
"""The repository's object-store pin: one image, tag + digest, same in compose and CI."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
PIN = re.compile(r"^[\w./-]+:RELEASE\.[\w.-]+@sha256:[0-9a-f]{64}$")


@pytest.mark.trace("REQ-INFRA-013")
def test_the_server_and_the_bucket_one_shot_share_one_pinned_image() -> None:
    server = COMPOSE["services"]["minio"]["image"]
    one_shot = COMPOSE["services"]["minio_init"]["image"]

    assert server == one_shot, "the bucket step runs in the server image (it contains mc)"
    assert PIN.match(server), f"{server!r} is not a release tag plus an index digest"
    assert not server.startswith("quay.io/")


@pytest.mark.trace("REQ-INFRA-013")
def test_ci_names_the_identical_image_for_the_server_and_for_the_bucket() -> None:
    server = COMPOSE["services"]["minio"]["image"]
    assert CI.count(server) == 2, (
        "the workflow must start the server and create the bucket from the compose pin"
    )
    assert not re.search(r"quay\.io/minio", CI)


@pytest.mark.trace("REQ-INFRA-013")
def test_no_tracked_configuration_still_names_an_image_that_is_not_served() -> None:
    files = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "docker-compose.yml",
            "Dockerfile",
            "apps/web/Dockerfile",
            ".github",
            "docs",
            "Makefile",
            "deploy",
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    offenders = [
        name.decode()
        for name in files
        if name
        and "quay.io/minio" in (ROOT / name.decode()).read_text(errors="ignore")
        and not name.decode().startswith("docs/superpowers")
    ]
    assert offenders == []


@pytest.mark.trace("REQ-INFRA-013")
def test_the_health_check_and_the_bucket_step_still_use_mc() -> None:
    assert "mc ready local" in " ".join(COMPOSE["services"]["minio"]["healthcheck"]["test"])
    entrypoint = COMPOSE["services"]["minio_init"]["entrypoint"]
    assert "mc mb --ignore-existing" in entrypoint and "mc alias set" in entrypoint
