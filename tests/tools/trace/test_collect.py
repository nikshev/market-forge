import pytest

from tools.trace.collect import (
    PRD_NODE_ID,
    collect_code,
    collect_decisions,
    collect_outcomes,
    collect_requirements,
    collect_specs,
)


def test_collects_one_node_per_requirement(vault):
    vault.requirement("REQ-WP-001")
    vault.requirement("REQ-WP-002")
    nodes, _ = collect_requirements(vault.vault)
    assert sorted(n.id for n in nodes) == ["REQ-WP-001", "REQ-WP-002"]
    assert {n.kind for n in nodes} == {"requirement"}


def test_requirement_carries_status_and_type_in_attrs(vault):
    vault.requirement("REQ-WP-001", status="implemented", type_="work-package")
    nodes, _ = collect_requirements(vault.vault)
    assert nodes[0].attrs["status"] == "implemented"
    assert nodes[0].attrs["type"] == "work-package"


def test_requirement_links_back_to_the_prd(vault):
    vault.requirement("REQ-WP-001", prd_ref="§46 WP-001")
    _, edges = collect_requirements(vault.vault)
    derived = [(e.src, e.dst) for e in edges if e.kind == "DERIVED_FROM"]
    assert derived == [("REQ-WP-001", PRD_NODE_ID)]


def test_depends_on_becomes_edges(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002", "REQ-WP-003"])
    _, edges = collect_requirements(vault.vault)
    deps = sorted(e.dst for e in edges if e.kind == "DEPENDS_ON")
    assert deps == ["REQ-WP-002", "REQ-WP-003"]


def test_gitkeep_and_templates_are_ignored(vault):
    (vault.vault / "10-requirements" / ".gitkeep").write_text("")
    vault.requirement("REQ-WP-001")
    nodes, _ = collect_requirements(vault.vault)
    assert len(nodes) == 1


def test_requirement_without_an_id_field_raises_naming_the_file(vault):
    bad = vault.vault / "10-requirements" / "REQ-WP-009.md"
    bad.write_text("---\ntitle: no id here\n---\n\nbody\n")
    with pytest.raises(ValueError, match="REQ-WP-009.md: missing 'id'"):
        collect_requirements(vault.vault)


def test_requirement_id_must_match_its_filename(vault):
    bad = vault.vault / "10-requirements" / "REQ-WP-010.md"
    bad.write_text("---\nid: REQ-WP-999\n---\n\nbody\n")
    with pytest.raises(ValueError, match="id 'REQ-WP-999' does not match filename"):
        collect_requirements(vault.vault)


def test_specs_produce_specifies_edges(vault):
    vault.spec("001-bootstrap", ["REQ-WP-001", "REQ-WP-002"])
    nodes, edges = collect_specs(vault.specs)
    assert nodes[0].id == "SPEC-001-bootstrap"
    assert nodes[0].kind == "spec"
    assert sorted(e.dst for e in edges if e.kind == "SPECIFIES") == ["REQ-WP-001", "REQ-WP-002"]


def test_spec_with_empty_traces_yields_a_node_but_no_edges(vault):
    vault.spec("002-empty", [])
    nodes, edges = collect_specs(vault.specs)
    assert len(nodes) == 1
    assert edges == []


def test_outcomes_produce_records_edges(vault):
    vault.outcome("OUT-2026-09-07-spec-bootstrap", step="spec", records=["REQ-WP-001"])
    nodes, edges = collect_outcomes(vault.vault)
    assert nodes[0].kind == "outcome"
    assert nodes[0].attrs["step"] == "spec"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("OUT-2026-09-07-spec-bootstrap", "REQ-WP-001", "RECORDS")
    ]


def test_decisions_produce_decides_edges(vault):
    vault.decision("ADR-001", ["REQ-WP-001"])
    nodes, edges = collect_decisions(vault.vault)
    assert nodes[0].kind == "decision"
    assert [(e.src, e.dst, e.kind) for e in edges] == [("ADR-001", "REQ-WP-001", "DECIDES")]


def test_code_markers_produce_implements_edges(vault):
    vault.source("channelflow/bars.py", ["REQ-WP-005"])
    nodes, edges = collect_code([vault.root / "src"])
    assert nodes[0].kind == "code"
    assert nodes[0].id == "src/channelflow/bars.py"
    assert [(e.src, e.dst, e.kind) for e in edges] == [
        ("src/channelflow/bars.py", "REQ-WP-005", "IMPLEMENTS")
    ]


def test_a_file_with_two_markers_yields_one_node_and_two_edges(vault):
    vault.source("channelflow/channels.py", ["REQ-WP-006", "REQ-BIAS-002"])
    nodes, edges = collect_code([vault.root / "src"])
    assert len(nodes) == 1
    assert len(edges) == 2


def test_files_without_markers_produce_no_nodes(vault):
    (vault.root / "src" / "plain.py").write_text("def f():\n    return 1\n")
    nodes, edges = collect_code([vault.root / "src"])
    assert nodes == []
    assert edges == []


def test_code_collection_skips_pycache(vault):
    cache = vault.root / "src" / "__pycache__"
    cache.mkdir()
    (cache / "stale.py").write_text("# @trace: REQ-WP-001\n")
    nodes, _ = collect_code([vault.root / "src"])
    assert nodes == []
