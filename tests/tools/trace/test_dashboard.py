from pathlib import Path

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


def test_replace_between_markers_rejects_a_begin_marker_with_no_end():
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers(f"{BEGIN}\nx\n", "new")


def test_replace_between_markers_rejects_an_end_marker_with_no_begin():
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers(f"{END}\nx\n", "new")


def test_replace_between_markers_rejects_prose_that_mentions_both_markers_in_one_sentence():
    """Variant A: a sentence explaining the convention contains both markers as
    literal text, ahead of the real, separate trace block. A naive first-`find()`
    implementation would splice the new block into the middle of that sentence
    and leave the real block stale and untouched -- silent corruption. This must
    raise instead.
    """
    text = (
        "## Convention\n"
        f"The generated block goes between {BEGIN} and {END} in every note.\n\n"
        "## Trace\n"
        f"{BEGIN}\n"
        "_Not yet generated._\n"
        f"{END}\n"
    )
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers(text, "new")


def test_replace_between_markers_rejects_a_stray_begin_mention_before_the_real_pair():
    """Variant B: prose mentions only BEGIN, ahead of the real pair further down.
    A naive first-`find()` implementation would treat the prose mention as the
    start of the block and the real END as its close, silently eating every
    hand-written section in between -- here, the whole '## Acceptance' section.
    This must raise instead of destroying that content.
    """
    text = (
        "## Requirement\n"
        f"The generated block starts at {BEGIN} and the tool never writes outside it.\n\n"
        "## Acceptance\n"
        "- Nothing outside the markers is modified.\n\n"
        "## Trace\n"
        f"{BEGIN}\n"
        "_No linked artifacts yet._\n"
        f"{END}\n"
    )
    with pytest.raises(ValueError, match="marker pair not found"):
        replace_between_markers(text, "new")


def test_update_requirement_notes_skips_and_preserves_a_note_that_mentions_markers_in_prose(vault):
    """The content-preservation half of variant B: run it through the real
    entry point and assert the file on disk is byte-for-byte untouched, not
    merely that an exception was raised somewhere.
    """
    path = vault.vault / "10-requirements" / "REQ-WP-001.md"
    original = (
        "---\nid: REQ-WP-001\nstatus: draft\n---\n\n"
        "## Requirement\n"
        f"The generated block starts at {BEGIN} and the tool never writes outside it.\n\n"
        "## Acceptance\n"
        "- Nothing outside the markers is modified.\n\n"
        "## Trace\n"
        f"{BEGIN}\n"
        "_No linked artifacts yet._\n"
        f"{END}\n"
    )
    path.write_text(original)
    graph = build_graph(vault.root)

    updated, skipped = update_requirement_notes(graph)

    assert updated == []
    assert skipped == [path]
    assert path.read_text() == original


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


def _write_requirement_with_phase(vault, req_id: str, phase: str) -> Path:
    """VaultBuilder.requirement() hardcodes `phase: 0`, so a requirement note is
    built directly here to exercise this project's real phase vocabulary
    (0-8 plus 1A and 7A), without touching conftest.py.
    """
    path = vault.vault / "10-requirements" / f"{req_id}.md"
    path.write_text(
        "---\n"
        f"id: {req_id}\n"
        "title: A requirement\n"
        "type: work-package\n"
        'prd_ref: "§1"\n'
        f"phase: {phase}\n"
        "status: draft\n"
        "depends_on: []\n"
        "---\n\n"
        "## Requirement\n\nBody.\n\n"
        "## Trace\n\n<!-- trace:begin -->\n_Not yet generated._\n<!-- trace:end -->\n\n"
        "## Notes\n\nHand-written.\n"
    )
    return path


def test_dashboard_groups_this_projects_real_phases_in_sane_order(vault):
    phases = ["0", "1", "1A", "2", "3", "4", "5", "6", "7", "7A", "8"]
    for index, phase in enumerate(phases):
        _write_requirement_with_phase(vault, f"REQ-WP-{index:03d}", phase)
    graph = build_graph(vault.root)

    text = render_dashboard(graph, validate(graph))

    positions = [text.index(f"### Phase {phase}") for phase in phases]
    assert positions == sorted(positions)
    # The unfiltered view comes first, ahead of every per-phase diagram.
    assert text.index("### All requirements") < min(positions)


def test_dashboard_all_requirements_diagram_includes_a_phaseless_requirement(vault):
    """A requirement with `phase: null` (most of this project's real
    requirements -- the PRD doesn't assign every requirement a phase) never
    appears in any per-phase diagram. It must still be visible somewhere:
    the unfiltered "All requirements" diagram is that somewhere.
    """
    _write_requirement_with_phase(vault, "REQ-WP-000", "0")
    vault.requirement("REQ-INFRA-001")  # phase: 0 via the fixture default

    path = vault.vault / "10-requirements" / "REQ-INFRA-001.md"
    text = path.read_text().replace("phase: 0", "phase: null")
    path.write_text(text)

    graph = build_graph(vault.root)
    dashboard = render_dashboard(graph, validate(graph))

    all_section = dashboard.split("### All requirements", 1)[1].split("### Phase", 1)[0]
    assert "REQ_INFRA_001[" in all_section
    # And it must not show up in the phase-0 diagram, which only phase: 0
    # requirements (and their neighbours) belong to.
    phase_0_section = dashboard.split("### Phase 0", 1)[1]
    assert "REQ_INFRA_001" not in phase_0_section


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


def test_write_dashboard_does_not_rewrite_when_content_is_unchanged(vault, tmp_path, monkeypatch):
    """update_requirement_notes already guards its write with `if new_text != text`;
    write_dashboard must do the same, or every `make graph` run touches the
    dashboard's mtime and dirties the tree even when nothing changed.

    A monkeypatched `Path.write_text` is used instead of comparing mtimes: on
    some filesystems (e.g. HFS+'s one-second mtime resolution) two writes made
    within the same test could report an unchanged mtime even if a write did
    happen, making an mtime-based assertion flaky. Forbidding the call outright
    is deterministic.
    """
    target = tmp_path / "Traceability Dashboard.md"
    target.write_text(f"# Traceability Dashboard\n\n{BEGIN}\nstale\n{END}\n")
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    violations = validate(graph)

    write_dashboard(graph, violations, target)
    first_write = target.read_text()
    assert "REQ-WP-001" in first_write

    def _forbid_write(self, *args, **kwargs):
        raise AssertionError(f"write_text called unexpectedly on unchanged content: {self}")

    monkeypatch.setattr(Path, "write_text", _forbid_write)
    write_dashboard(graph, violations, target)


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


@pytest.mark.trace("REQ-INFRA-001")
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
