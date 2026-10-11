# @trace: REQ-INFRA-013
"""Is each image still served? gone / unknown / served, and the exit code (FR-005, FR-006)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.images.__main__ import main
from tools.images.resolve import classify, docker_runner

# Real error texts: the first two are what CI and `docker manifest inspect` said on 2026-10-11.
GONE = [
    "docker: Error response from daemon: unauthorized: access to the requested resource "
    "is not authorized",
    "Error response from daemon: pull access denied for minio/minio, repository does not exist "
    "or may require 'docker login'",
    "no such manifest: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z",
    "manifest unknown: manifest unknown",
    "Error response from daemon: manifest for acme/x:9 not found: "
    "manifest unknown: manifest unknown",
    "name unknown: repository name not known to registry",
    "unauthorized: authentication required",
    "denied: requested access to the resource is denied",
    # quay's answer for a repository that was removed (ADR-069): an anonymous client cannot tell
    # it from "not for you", and neither can the check.
    "Requires authentication",
    "authentication required",
]
UNKNOWN = [
    "toomanyrequests: You have reached your pull rate limit.",
    'Error response from daemon: Head "https://registry-1.docker.io/v2/x/manifests/1": '
    "net/http: TLS handshake timeout",
    "dial tcp: lookup registry-1.docker.io: no such host",
    'Get "https://quay.io/v2/": dial tcp 1.2.3.4:443: connect: connection refused',
    "received unexpected HTTP status: 429 Too Many Requests",
    "i/o timeout",
    "toomanyrequests: retry later",
    "You have reached your pull limit; the rate limit resets in six hours",
    "net/http: request canceled (Client.Timeout exceeded while awaiting headers) timed out",
    "Temporary failure in name resolution",
    # Both kinds of words at once: could not ask wins, so a throttled reply that also mentions
    # a denial is not reported as the image being gone.
    "429 Too Many Requests: unauthorized: authentication required",
]


@pytest.mark.trace("REQ-INFRA-013")
@pytest.mark.parametrize("text", GONE)
def test_the_registry_saying_it_does_not_have_the_image_is_gone(text: str) -> None:
    assert classify(1, text) == "gone"


@pytest.mark.trace("REQ-INFRA-013")
@pytest.mark.parametrize("text", UNKNOWN)
def test_a_rate_limit_or_a_network_failure_is_unknown_never_gone(text: str) -> None:
    assert classify(1, text) == "unknown"


@pytest.mark.trace("REQ-INFRA-013")
def test_success_is_served_and_an_unrecognised_failure_is_unknown_not_gone() -> None:
    assert classify(0, "") == "served"
    assert classify(1, "something nobody has seen before") == "unknown"


def repo_with(tmp_path: Path, *images: str) -> Path:
    body = "services:\n" + "".join(
        f"  s{i}:\n    image: {image}\n" for i, image in enumerate(images)
    )
    (tmp_path / "docker-compose.yml").write_text(body)
    return tmp_path


@pytest.mark.trace("REQ-INFRA-013")
def test_the_command_exits_one_naming_the_image_and_where_it_is_referenced(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = repo_with(tmp_path, "postgres:16", "quay.io/minio/minio:RELEASE.X")

    def runner(reference: str) -> tuple[int, str]:
        return (
            (1, "unauthorized: access to the requested resource is not authorized")
            if "quay.io" in reference
            else (0, "")
        )

    code = main(["--root", str(root)], runner=runner)

    out = capsys.readouterr().out
    assert code == 1
    assert (
        "quay.io/minio/minio:RELEASE.X" in out
        and "docker-compose.yml" in out
        and "no longer served" in out
    )
    assert "postgres:16" in out  # the ones that are fine are listed too


@pytest.mark.trace("REQ-INFRA-013")
def test_the_command_exits_zero_when_everything_is_served_or_merely_unknown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = repo_with(tmp_path, "postgres:16", "grafana/grafana:12")

    def runner(reference: str) -> tuple[int, str]:
        return (
            (1, "toomanyrequests: You have reached your pull rate limit.")
            if "grafana" in reference
            else (0, "")
        )

    assert main(["--root", str(root)], runner=runner) == 0
    out = capsys.readouterr().out
    assert "unknown" in out and "rate limit" in out


@pytest.mark.trace("REQ-INFRA-013")
def test_an_image_the_check_cannot_read_fails_the_run_instead_of_vanishing(tmp_path: Path) -> None:
    (tmp_path / "docker-compose.yml").write_text("services:\n  s:\n    image: ${NO_DEFAULT}\n")
    assert main(["--root", str(tmp_path)], runner=lambda reference: (0, "")) == 1


@pytest.mark.trace("REQ-INFRA-013")
def test_each_distinct_reference_is_asked_about_once(tmp_path: Path) -> None:
    root = repo_with(tmp_path, "postgres:16", "postgres:16", "redis:7")
    asked: list[str] = []

    def runner(reference: str) -> tuple[int, str]:
        asked.append(reference)
        return (0, "")

    main(["--root", str(root)], runner=runner)
    assert sorted(asked) == ["postgres:16", "redis:7"]


@pytest.mark.trace("REQ-INFRA-013")
def test_a_docker_that_hangs_or_is_missing_is_unknown_never_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def hangs(*args: object, **kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="docker", timeout=90)

    monkeypatch.setattr(subprocess, "run", hangs)
    assert classify(*docker_runner("postgres:16")) == "unknown"

    def absent(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("docker")

    monkeypatch.setattr(subprocess, "run", absent)
    assert classify(*docker_runner("postgres:16")) == "unknown"
