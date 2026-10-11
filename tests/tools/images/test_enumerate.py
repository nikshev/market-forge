# @trace: REQ-INFRA-013
"""Which images does the repository name? Parsing only; no network (FR-004, FR-007)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.images.enumerate import ImageRef, enumerate_images, parse_reference

ROOT = Path(__file__).resolve().parents[3]


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def names(found) -> set[str]:  # type: ignore[no-untyped-def]
    return {ref.reference for ref in found.images}


@pytest.mark.trace("REQ-INFRA-013")
@pytest.mark.parametrize(
    ("text", "name", "tag", "digest"),
    [
        ("postgres:16-alpine3.24", "postgres", "16-alpine3.24", None),
        ("postgres", "postgres", None, None),
        (
            "quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z",
            "quay.io/minio/minio",
            "RELEASE.2025-09-07T16-13-09Z",
            None,
        ),
        (
            "docker.io/pgsty/minio:RELEASE.X@sha256:" + "ab" * 32,
            "docker.io/pgsty/minio",
            "RELEASE.X",
            "sha256:" + "ab" * 32,
        ),
        ("localhost:5000/team/img:1.2", "localhost:5000/team/img", "1.2", None),
        (
            "ghcr.io/astral-sh/uv@sha256:" + "cd" * 32,
            "ghcr.io/astral-sh/uv",
            None,
            "sha256:" + "cd" * 32,
        ),
    ],
)
def test_a_reference_is_split_into_name_tag_and_digest(
    text: str, name: str, tag: str | None, digest: str | None
) -> None:
    ref = parse_reference(text, where="x:1")
    assert (ref.name, ref.tag, ref.digest) == (name, tag, digest)
    assert ref.reference == text  # what a registry is asked about is exactly what was written


@pytest.mark.trace("REQ-INFRA-013")
def test_compose_images_are_found_in_every_profile_with_defaults_resolved_and_built_images_skipped(
    tmp_path: Path,
) -> None:
    write(
        tmp_path,
        "docker-compose.yml",
        """
x-store: &store docker.io/acme/store:1.0@sha256:%s
services:
  db:
    image: postgres:16
  store:
    image: *store
  store_init:
    image: *store
  tunnel:
    profiles: [tunnel]
    image: ${TUNNEL_IMAGE:-cloudflare/cloudflared:2026.9.3}
  api:
    build: {context: .}
    image: channelflow-api
  broken:
    image: ${NO_DEFAULT}
"""
        % ("ab" * 32),
    )
    found = enumerate_images(tmp_path)

    assert names(found) == {
        "postgres:16",
        "docker.io/acme/store:1.0@sha256:" + "ab" * 32,
        "cloudflare/cloudflared:2026.9.3",
    }
    assert any("NO_DEFAULT" in u for u in found.unresolved), (
        "a variable with no default is reported, not dropped"
    )
    assert all("channelflow-api" not in r.reference for r in found.images)  # built locally


@pytest.mark.trace("REQ-INFRA-013")
def test_dockerfile_from_and_copy_from_are_found_and_stage_names_are_not_images(
    tmp_path: Path,
) -> None:
    write(
        tmp_path,
        "Dockerfile",
        """
ARG BASE=alpine:3.20
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv
FROM --platform=linux/amd64 python:3.12-slim AS runtime
COPY --from=build --chown=u:u /opt/venv /opt/venv
FROM build AS extra
FROM scratch
FROM ${BASE}
FROM ${NO_DEFAULT_ARG}
""",
    )
    found = enumerate_images(tmp_path)

    # An ARG declared before the first FROM with a default is substituted, as Docker does.
    assert names(found) == {"python:3.12-slim", "ghcr.io/astral-sh/uv:0.5.11", "alpine:3.20"}
    assert any("NO_DEFAULT_ARG" in u for u in found.unresolved), (
        "an ARG with no default is reported"
    )


@pytest.mark.trace("REQ-INFRA-013")
def test_the_workflow_services_and_multi_line_docker_run_commands_are_found(tmp_path: Path) -> None:
    write(
        tmp_path,
        ".github/workflows/ci.yml",
        """
name: CI
jobs:
  gate:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine3.24
        env: {A: b}
    steps:
      - uses: actions/checkout@v4
      - name: Start the object store
        run: |
          docker run -d --name minio \\
            -p 9000:9000 \\
            -e MINIO_ROOT_USER=u \\
            docker.io/acme/store:1.0 server /data
          echo not an image: nginx
      - name: Bucket
        run: |
          docker run --rm --network host --entrypoint /bin/sh \\
            docker.io/acme/store:1.0 -c "mc mb x"
      - name: Build
        run: docker build -t local-thing .
""",
    )
    found = enumerate_images(tmp_path)
    assert names(found) == {"postgres:16-alpine3.24", "docker.io/acme/store:1.0"}
    store = [r for r in found.images if r.name == "docker.io/acme/store"]
    assert len(store) == 2 and all(".github/workflows/ci.yml" in r.where for r in store)


@pytest.mark.trace("REQ-INFRA-013")
def test_the_real_repository_names_the_registry_images_it_is_known_to_use() -> None:
    found = enumerate_images(ROOT)
    refs = names(found)
    wanted = (
        "postgres:",
        "redpandadata/redpanda:",
        "prom/prometheus:",
        "grafana/grafana:",
        "cloudflare/cloudflared:",
    )
    for prefix in wanted:
        assert any(r.startswith(prefix) for r in refs), prefix
    for base in ("python:3.12-slim", "node:22-alpine", "nginx:1.27-alpine"):
        assert base in refs, base
    assert any("/uv:" in r for r in refs)
    assert any("minio" in r for r in refs), "the object store is among them"
    assert not [r for r in refs if "channelflow-" in r], "locally built images are not pulled"
    assert found.unresolved == [], found.unresolved
    assert all(isinstance(r, ImageRef) for r in found.images)
