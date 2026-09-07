import json

import pytest

from tools.trace.cli import main


def test_build_writes_the_graph_json(vault, capsys):
    vault.requirement("REQ-WP-001")
    code = main(["build", "--repo-root", str(vault.root)])
    assert code == 0
    payload = json.loads((vault.root / ".trace" / "graph.json").read_text())
    assert any(n["id"] == "REQ-WP-001" for n in payload["nodes"])


def test_validate_exits_zero_when_clean(vault, capsys):
    vault.requirement("REQ-WP-001", status="draft")
    assert main(["validate", "--repo-root", str(vault.root)]) == 0
    assert "clean" in capsys.readouterr().out.lower()


@pytest.mark.trace("REQ-INFRA-001")
def test_validate_exits_one_and_names_the_rule(vault, capsys):
    vault.requirement("REQ-WP-001", status="specified")
    code = main(["validate", "--repo-root", str(vault.root)])
    out = capsys.readouterr().out
    assert code == 1
    assert "R1" in out
    assert "REQ-WP-001" in out


def test_show_prints_the_linked_artifacts(vault, capsys):
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    assert main(["show", "REQ-WP-001", "--repo-root", str(vault.root)]) == 0
    assert "SPEC-001-bootstrap" in capsys.readouterr().out


def test_show_of_an_unknown_requirement_exits_two(vault, capsys):
    code = main(["show", "REQ-WP-404", "--repo-root", str(vault.root)])
    assert code == 2
    assert "REQ-WP-404" in capsys.readouterr().err


def test_dashboard_updates_the_file_and_the_notes(vault):
    dashboard = vault.vault / "00-index" / "Traceability Dashboard.md"
    dashboard.write_text(
        "# Traceability Dashboard\n\n<!-- trace:begin -->\nstale\n<!-- trace:end -->\n"
    )
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])

    assert main(["dashboard", "--repo-root", str(vault.root)]) == 0

    assert "REQ-WP-001" in dashboard.read_text()
    assert "SPEC-001-bootstrap" in (vault.vault / "10-requirements" / "REQ-WP-001.md").read_text()


def test_a_collector_error_exits_one_instead_of_raising(vault, capsys):
    """A malformed note must fail the build with a message, never a traceback."""
    vault.requirement("REQ-WP-001")
    (vault.vault / "10-requirements" / "REQ-WP-002.md").write_text(
        "---\nid: REQ-WP-001\nstatus: draft\n---\n\nbody\n"
    )
    code = main(["validate", "--repo-root", str(vault.root)])
    assert code == 1
    err = capsys.readouterr().err
    assert "cannot build graph" in err
    assert "REQ-WP-002.md" in err


def test_dashboard_with_a_broken_marker_pair_exits_one_instead_of_raising(vault, capsys):
    """A bad marker pair in the dashboard file must fail with a message, never a traceback."""
    dashboard = vault.vault / "00-index" / "Traceability Dashboard.md"
    dashboard.write_text(
        "# Traceability Dashboard\n\n"
        "<!-- trace:begin -->\nstale\n<!-- trace:end -->\n"
        "<!-- trace:end -->\n"
    )
    vault.requirement("REQ-WP-001")

    code = main(["dashboard", "--repo-root", str(vault.root)])
    assert code == 1
    err = capsys.readouterr().err
    assert "dashboard" in err.lower()
    assert str(dashboard) in err
