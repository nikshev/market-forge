"""How the read API starts, and how it refuses to (REQ-WP-064).

PRD §6.2 names an `api` service. Before this there was no way to run one: a
factory taking an already-built repository, and a catalog opened only in a test
fixture pointing at a temporary directory.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from channelflow.api.app import create_app
from channelflow.api.main import (
    CATALOG_URI,
    REQUIRED,
    WAREHOUSE,
    MissingConfiguration,
    Settings,
    build_app,
    settings_from_env,
)
from channelflow.api.readiness import NOT_READY, Readiness, always_ready, catalog_probe
from channelflow.api.repositories import InMemoryRepository

ROOT = Path(__file__).resolve().parents[3]


def _env(**overrides: str) -> dict[str, str]:
    base = {CATALOG_URI: "sqlite:///tmp/catalog.db", WAREHOUSE: "/tmp/warehouse"}
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-064")
def test_the_required_configuration_is_read() -> None:
    settings = settings_from_env(_env())

    assert settings.catalog_uri == "sqlite:///tmp/catalog.db"
    assert settings.warehouse == "/tmp/warehouse"
    assert settings.storage == {}


@pytest.mark.trace("REQ-WP-064")
def test_both_variables_are_required() -> None:
    """Written out rather than read from `REQUIRED`.

    The parametrised test below takes its cases from that tuple, so shortening
    the tuple removes the case that would have caught it -- the sweep found
    exactly that. A list that pins itself pins nothing.
    """
    assert set(REQUIRED) == {"CHANNELFLOW_CATALOG_URI", "CHANNELFLOW_WAREHOUSE"}


@pytest.mark.trace("REQ-WP-064")
@pytest.mark.parametrize("missing", ["CHANNELFLOW_CATALOG_URI", "CHANNELFLOW_WAREHOUSE"])
def test_a_missing_variable_refuses_to_start_and_names_itself(missing: str) -> None:
    """The default that would be convenient is a local directory, and a process
    serving an empty warehouse is indistinguishable from a quiet market."""
    environment = {name: value for name, value in _env().items() if name != missing}

    with pytest.raises(MissingConfiguration, match=missing):
        settings_from_env(environment)


@pytest.mark.trace("REQ-WP-064")
@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_a_blank_variable_counts_as_missing(blank: str) -> None:
    """An empty variable is what a shell gives for one nobody set. A catalog URI
    of `""` would fail later and elsewhere -- inside pyiceberg, about a URL --
    rather than here, about a deployment."""
    with pytest.raises(MissingConfiguration, match=CATALOG_URI):
        settings_from_env(_env(**{CATALOG_URI: blank}))


@pytest.mark.trace("REQ-WP-064")
def test_both_missing_variables_are_named_at_once() -> None:
    with pytest.raises(MissingConfiguration) as raised:
        settings_from_env({})

    for name in ("CHANNELFLOW_CATALOG_URI", "CHANNELFLOW_WAREHOUSE"):
        assert name in str(raised.value)


@pytest.mark.trace("REQ-WP-064")
def test_storage_options_are_read_under_pyicebergs_names() -> None:
    settings = settings_from_env(
        _env(
            CHANNELFLOW_S3_ENDPOINT="http://minio:9000",
            CHANNELFLOW_S3_ACCESS_KEY_ID="key",
            CHANNELFLOW_S3_SECRET_ACCESS_KEY="secret",
            CHANNELFLOW_S3_REGION="",
        )
    )

    assert settings.storage == {
        "s3.endpoint": "http://minio:9000",
        "s3.access-key-id": "key",
        "s3.secret-access-key": "secret",
    }, "a blank option is absent, not an empty region"


# --------------------------------------------------------------------------
# Readiness
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-064")
def test_the_application_is_built_from_configuration_alone(tmp_path: Path) -> None:
    app = build_app(
        Settings(
            catalog_uri=f"sqlite:///{tmp_path}/catalog.db",
            warehouse=str(tmp_path),
            storage={},
        )
    )

    with TestClient(app) as client:
        answer = client.get("/readyz")

    assert answer.status_code == 200
    assert answer.json() == {"ready": True, "detail": "the catalog answered"}


@pytest.mark.trace("REQ-WP-064")
def test_a_store_that_does_not_answer_is_not_ready() -> None:
    """A ping is not enough: a process that started and cannot read its
    warehouse serves empty results, and an empty result is this system's most
    dangerous shape."""

    def broken() -> object:
        raise ConnectionError("terminating connection due to administrator command")

    answer = catalog_probe(broken)()

    assert answer.ready is False
    assert "administrator command" in answer.detail


@pytest.mark.trace("REQ-WP-064")
def test_an_unready_process_answers_with_a_status_an_orchestrator_reads() -> None:
    def probe() -> Readiness:
        return Readiness(ready=False, detail="the catalog did not answer")

    app = create_app(repository=InMemoryRepository(), readiness=probe)

    with TestClient(app) as client:
        answer = client.get("/readyz")

    # The literal, not the constant the route reads: comparing a response
    # against the value that produced it asserts nothing.
    assert answer.status_code == 503
    assert NOT_READY == 503
    assert answer.json()["ready"] is False


@pytest.mark.trace("REQ-WP-064")
def test_an_app_with_no_store_says_so_rather_than_claiming_one_answered() -> None:
    app = create_app(repository=InMemoryRepository())

    with TestClient(app) as client:
        answer = client.get("/readyz")

    assert answer.json() == {"ready": True, "detail": "no store is configured"}
    assert always_ready("x")().detail == "x"


@pytest.mark.trace("REQ-WP-064")
def test_readiness_is_not_section_32s_feed_health() -> None:
    """Answering a container probe with §32's state would have an orchestrator
    restart a pod because a venue went quiet, and would call a process that
    cannot reach its catalog healthy whenever the feeds were fine."""
    module = ast.parse((ROOT / "src" / "channelflow" / "api" / "readiness.py").read_text())
    imported = {
        node.module
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    # The docstring names `HealthState` to say why it is not used, so the check
    # is on what the module imports rather than on what it mentions.
    assert not any(name.startswith("channelflow.health") for name in imported)
    assert "channelflow.health" not in imported


# --------------------------------------------------------------------------
# The images and the compose file
# --------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-064")
def test_the_api_image_installs_the_project_without_a_path_link() -> None:
    """An editable install writes a link to the build stage's source tree, which
    the runtime stage does not copy. The image then builds, starts, and fails to
    import its own package -- caught by running it, not by reading it."""
    dockerfile = (ROOT / "Dockerfile").read_text()

    assert "--no-editable" in dockerfile
    assert "--frozen" in dockerfile, "the lockfile, not a fresh resolution"


@pytest.mark.trace("REQ-WP-064")
def test_the_compose_file_declares_the_services_that_exist() -> None:
    compose = (ROOT / "docker-compose.yml").read_text()

    assert re.search(r"^  api:$", compose, re.M)
    assert re.search(r"^  web:$", compose, re.M)
    # §6.2 also names these, and neither exists as code. A container running
    # nothing is worse than an absent one: it reports healthy.
    assert not re.search(r"^  worker:$", compose, re.M)
    assert not re.search(r"^  ingest-binance:$", compose, re.M)


@pytest.mark.trace("REQ-WP-064")
def test_no_credential_is_written_into_the_compose_file() -> None:
    """§34: credentials live in the environment. Every value the API service
    takes is a reference, so the file can be read by anyone."""
    compose = (ROOT / "docker-compose.yml").read_text()
    service = compose.split("  api:", 1)[1].split("\n  web:", 1)[0]

    for line in service.splitlines():
        if "PASSWORD" in line or "SECRET" in line or "ACCESS_KEY" in line:
            assert "${" in line, f"a literal credential in the compose file: {line.strip()}"


@pytest.mark.trace("REQ-WP-064")
def test_the_build_context_excludes_the_developers_environment() -> None:
    """A `.env` inside a build context is a credential inside an image's inputs,
    which is what §34 exists to prevent."""
    ignored = (ROOT / ".dockerignore").read_text().splitlines()

    assert ".env" in ignored
    assert ".venv" in ignored
    assert "!.env.example" in ignored
