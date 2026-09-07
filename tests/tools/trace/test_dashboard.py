import pytest

from tools.trace.dashboard import (
    BEGIN,
    END,
    render_dashboard,
    render_requirement_trace,
    replace_between_markers,
    update_requirement_notes,
    write_dashboard,
)
from tools.trace.graph import build_graph
from tools.trace.validate import validate


def test_replace_between_markers_keeps_surrounding_text():
    text = f"# Title\n\nIntro paragraph.\n\n{BEGIN}\nold\n{END}\n\nTrailing words.\n"
    result = replace_between_markers(text, "new content")
    assert "Intro paragraph." in result
    assert "Trailing words." in result
    assert "old" not in result
    assert "new content" in result


def test_replace_between_markers_is_idempotent():
    text = f"{BEGIN}\nold\n{END}\n"
    once = replace_between_markers(text, "new")
    twice = replace_between_markers(once, "new")
    assert once == twice


def test_replace_between_markers_rejects_a_missing_pair():
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers("no markers here\n", "new")


def test_replace_between_markers_rejects_reversed_markers():
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers(f"{END}\nx\n{BEGIN}\n", "new")


def test_dashboard_lists_every_requirement_with_counts(vault, tmp_path):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-WP-001"])
    graph = build_graph(vault.root)
    text = render_dashboard(graph, validate(graph))
    assert "REQ-WP-001" in text
    assert "| specified |" in text


def test_dashboard_reports_violations(vault):
    vault.requirement("REQ-WP-001", status="specified")
    graph = build_graph(vault.root)
    text = render_dashboard(graph, validate(graph))
    assert "R1" in text
    assert "R4" in text


def test_dashboard_says_so_when_everything_passes(vault):
    vault.requirement("REQ-WP-001", status="draft")
    graph = build_graph(vault.root)
    text = render_dashboard(graph, validate(graph))
    assert "No violations." in text


def test_write_dashboard_preserves_handwritten_text(vault, tmp_path):
    target = tmp_path / "Traceability Dashboard.md"
    target.write_text(
        f"# Traceability Dashboard\n\nA hand-written preamble.\n\n{BEGIN}\nstale\n{END}\n"
    )
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    write_dashboard(graph, validate(graph), target)

    result = target.read_text()
    assert "A hand-written preamble." in result
    assert "stale" not in result
    assert "REQ-WP-001" in result


def test_requirement_trace_lists_linked_artifacts(vault, tmp_path):
    vault.requirement("REQ-WP-001", status="implemented")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.source("channelflow/bars.py", ["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')
    graph = build_graph(vault.root, test_dump=dump)

    block = render_requirement_trace(graph, "REQ-WP-001")
    assert "SPEC-001-bootstrap" in block
    assert "tests/test_a.py::test_x" in block
    assert "src/channelflow/bars.py" in block


def test_requirement_trace_says_none_when_nothing_links(vault):
    vault.requirement("REQ-WP-001")
    block = render_requirement_trace(build_graph(vault.root), "REQ-WP-001")
    assert "_No linked artifacts yet._" in block


def test_update_requirement_notes_preserves_the_notes_section(vault):
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    graph = build_graph(vault.root)

    updated, skipped = update_requirement_notes(graph)

    assert skipped == []
    text = (vault.vault / "10-requirements" / "REQ-WP-001.md").read_text()
    assert "Hand-written, never machine-rewritten." in text
    assert "SPEC-001-bootstrap" in text
    assert len(updated) == 1


def test_update_requirement_notes_is_idempotent(vault):
    vault.requirement("REQ-WP-001")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    graph = build_graph(vault.root)
    path = vault.vault / "10-requirements" / "REQ-WP-001.md"

    update_requirement_notes(graph)
    once = path.read_text()
    update_requirement_notes(build_graph(vault.root))
    assert path.read_text() == once


def test_update_requirement_notes_skips_notes_without_markers(vault):
    path = vault.vault / "10-requirements" / "REQ-WP-001.md"
    path.write_text("---\nid: REQ-WP-001\nstatus: draft\n---\n\n## Requirement\n\nNo markers.\n")
    graph = build_graph(vault.root)

    updated, skipped = update_requirement_notes(graph)

    assert updated == []
    assert skipped == [path]
    assert "No markers." in path.read_text()
