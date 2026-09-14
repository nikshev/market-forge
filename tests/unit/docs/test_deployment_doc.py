"""The deployment document is checked against the repository (REQ-WP-056).

Documentation rots in a way that looks exactly like documentation. A command
renamed, a service removed, a variable spelled differently -- each leaves prose
that is confident, plausible and wrong, and none of it fails anything.

So these tests read the document and the repository and compare them. They do not
check that the prose is good; they check that every name in it still exists.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from channelflow.observability.generate import DASHBOARD_PATH
from channelflow.observability.grafana import render

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs" / "deployment.md"
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"
MAKEFILE = ROOT / "Makefile"
PROMETHEUS = ROOT / "deploy" / "prometheus" / "prometheus.yml"


@pytest.fixture(scope="module")
def doc() -> str:
    assert DOC.is_file(), f"missing {DOC}"
    return DOC.read_text()


def _make_targets() -> set[str]:
    return set(re.findall(r"^([a-z][a-z-]*):", MAKEFILE.read_text(), re.M))


def _compose_services() -> set[str]:
    # The two-space-indented keys under `services:`; enough for this file's
    # shape and not a YAML parser, which would be a dependency for one check.
    body = COMPOSE.read_text().split("\nservices:\n", 1)[1].split("\nvolumes:", 1)[0]
    return set(re.findall(r"^  ([a-z][a-z_]*):", body, re.M))


def _env_names() -> set[str]:
    return set(re.findall(r"^([A-Z][A-Z0-9_]*)=", ENV_EXAMPLE.read_text(), re.M))


#: Where the document stops describing what runs and starts listing what does
#: not. The two sections carry tables of the same shape and opposite meaning, and
#: a check that read both would assert that `clickhouse` is in the compose file.
_NOT_RUNNING = "## What this stack deliberately does not run"


def _described_services(doc: str) -> set[str]:
    running, marker, rest = doc.partition(_NOT_RUNNING)
    assert marker, f"the document no longer has a {_NOT_RUNNING!r} section"
    assert rest, "the section is empty"
    return set(re.findall(r"^\| `([a-z][a-z_]*)` \|", running, re.M))


@pytest.mark.trace("REQ-WP-056")
def test_every_command_the_document_names_is_a_real_target(doc: str) -> None:
    """The classic rot: a target renamed and a document left behind."""
    targets = _make_targets()
    named = set(re.findall(r"^make ([a-z][a-z-]*)", doc, re.M))
    assert named, "the document names no commands"
    assert named <= targets, sorted(named - targets)


@pytest.mark.trace("REQ-WP-056")
def test_every_service_the_document_names_is_in_the_compose_file(doc: str) -> None:
    services = _compose_services()
    named = _described_services(doc)
    assert named, "the document names no services"
    assert named <= services, sorted(named - services)


@pytest.mark.trace("REQ-WP-056")
def test_every_running_service_is_described(doc: str) -> None:
    """The other direction, which is the one that goes quietly wrong: a service
    added to the stack and never mentioned is a service nobody knows is
    running.

    `minio_init` is excluded: it is a one-shot that creates the bucket and
    exits, not something a reader operates.
    """
    services = _compose_services() - {"minio_init"}
    named = _described_services(doc)
    assert services <= named, sorted(services - named)


@pytest.mark.trace("REQ-WP-056")
def test_every_variable_the_document_names_is_in_the_example(doc: str) -> None:
    known = _env_names()
    named = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", doc))
    assert named, "the document names no variables"
    assert named <= known, sorted(named - known)


@pytest.mark.trace("REQ-WP-056")
def test_every_variable_the_stack_needs_is_documented(doc: str) -> None:
    """A variable added to the example and never documented is a value somebody
    has to discover by reading a compose file."""
    named = set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", doc))
    assert _env_names() <= named, sorted(_env_names() - named)


@pytest.mark.trace("REQ-WP-056")
def test_the_example_carries_names_and_not_secrets() -> None:
    """PRD §34, and the rule `.env.example` has followed since [[REQ-WP-001]]:
    a credential here is a development default that says so in its own value."""
    for line in ENV_EXAMPLE.read_text().splitlines():
        if "TOKEN" in line or "CHAT_ID" in line:
            assert line.endswith("="), line


@pytest.mark.trace("REQ-WP-056")
def test_prometheus_scrapes_the_path_the_route_serves() -> None:
    """Asserted against the route rather than repeated, because a path copied
    into a config is a path that stops matching without anything failing."""
    from channelflow.api.metrics_route import router

    served = {route.path for route in router.routes}  # type: ignore[attr-defined]
    scraped = re.search(r"metrics_path: (\S+)", PROMETHEUS.read_text())
    assert scraped is not None
    assert scraped.group(1) in served


@pytest.mark.trace("REQ-WP-056")
def test_the_committed_dashboard_matches_the_definition() -> None:
    """A hand-edit, or a metric gaining a producer, fails here until the file is
    regenerated -- which is what makes regenerating it obligatory rather than
    remembered."""
    assert DASHBOARD_PATH.is_file(), f"missing {DASHBOARD_PATH}"
    assert DASHBOARD_PATH.read_text() == render()


@pytest.mark.trace("REQ-WP-056")
def test_the_dashboard_draws_what_exists_and_states_what_does_not() -> None:
    """Carried into the rendering: an absence is a text panel, not a graph of a
    metric nothing produces, because such a graph draws a flat line at zero and
    that reads as health."""
    from channelflow.observability import DASHBOARD

    document = json.loads(DASHBOARD_PATH.read_text())
    kinds = [panel["type"] for panel in document["panels"]]
    assert kinds.count("timeseries") == len(DASHBOARD.panels)
    assert kinds.count("text") == len(DASHBOARD.absences)

    for panel in document["panels"]:
        if panel["type"] == "text":
            assert "Nothing produces this metric" in panel["options"]["content"]


@pytest.mark.trace("REQ-WP-056")
def test_the_document_says_what_the_prd_lists_and_this_stack_does_not_run(doc: str) -> None:
    """A reader following §6.2 would look for a service nobody deploys and
    conclude the deployment is broken."""
    for absent in ("clickhouse", "redis", "Pinot"):
        assert absent in doc, absent
    # And each is accounted for rather than merely mentioned.
    assert "ADR-002" in doc
    assert "ADR-018" in doc


@pytest.mark.trace("REQ-WP-056")
def test_the_document_says_what_it_does_not_cover(doc: str) -> None:
    """A gap named is a gap somebody can plan around; a gap unmentioned is one
    they discover at the worst moment."""
    assert "not covered" in doc.lower()
    for gap in ("TLS", "Backups"):
        assert gap in doc, gap
    # "Load tests" left this list on 2026-09-14: `channelflow.perf.load` drives
    # §36's targets and REQ-PHASE-8 reached `implemented` on that acceptance
    # line. The document says where they went rather than dropping the subject.
    assert "Load tests are **no longer** on this list" in doc
