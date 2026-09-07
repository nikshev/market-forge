import json

from tools.trace.collect import PRD_NODE_ID
from tools.trace.graph import build_graph, to_dict, to_mermaid, to_networkx, write_json


def test_build_graph_includes_the_prd_as_a_request_node(vault):
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    assert graph.nodes[PRD_NODE_ID].kind == "request"


def test_build_graph_wires_every_edge_kind(vault, tmp_path):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-bootstrap", step="spec", records=["REQ-WP-001"])
    vault.decision("ADR-001", ["REQ-WP-001"])
    vault.source("channelflow/bars.py", ["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')

    graph = build_graph(vault.root, test_dump=dump)

    kinds = {e.kind for e in graph.edges}
    assert kinds == {
        "DERIVED_FROM",
        "DEPENDS_ON",
        "SPECIFIES",
        "RECORDS",
        "DECIDES",
        "IMPLEMENTS",
        "VERIFIES",
    }


def test_json_round_trips(vault, tmp_path):
    vault.requirement("REQ-WP-001")
    graph = build_graph(vault.root)
    out = tmp_path / "graph.json"
    write_json(graph, out)

    payload = json.loads(out.read_text())
    assert {n["id"] for n in payload["nodes"]} >= {"REQ-WP-001", PRD_NODE_ID}
    assert payload["edges"][0]["kind"] == "DERIVED_FROM"


def test_write_json_creates_missing_parents(vault, tmp_path):
    vault.requirement("REQ-WP-001")
    out = tmp_path / "deep" / "nested" / "graph.json"
    write_json(build_graph(vault.root), out)
    assert out.is_file()


def test_mermaid_of_an_empty_graph_is_still_valid(vault):
    graph = build_graph(vault.root)
    diagram = to_mermaid(graph)
    assert diagram.startswith("```mermaid\ngraph LR\n")
    assert diagram.rstrip().endswith("```")


def test_mermaid_escapes_quotes_in_titles(vault):
    vault.requirement("REQ-WP-001", title="A quoted title")
    (vault.vault / "10-requirements" / "REQ-WP-001.md").write_text(
        '---\nid: REQ-WP-001\ntitle: \'A "quoted" title\'\nstatus: draft\n---\n\nbody\n'
    )
    diagram = to_mermaid(build_graph(vault.root))
    label_line = next(
        line for line in diagram.split("\n") if line.strip().startswith("REQ_WP_001[")
    )
    # Mermaid labels are double-quoted, so the label must carry exactly two quotes.
    assert label_line.count('"') == 2
    assert "'quoted'" in label_line


def test_networkx_export_preserves_counts(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002")
    graph = build_graph(vault.root)
    digraph = to_networkx(graph)
    assert digraph.number_of_nodes() == len(graph.nodes)
    assert digraph.number_of_edges() == len(graph.edges)


def test_build_graph_is_deterministic(vault):
    vault.requirement("REQ-WP-002")
    vault.requirement("REQ-WP-001")
    first = to_dict(build_graph(vault.root))
    second = to_dict(build_graph(vault.root))
    assert first == second


def test_export_order_is_canonical_not_collector_insertion_order(vault, tmp_path):
    """The two-runs-agree determinism test cannot see whether the sorts exist,
    since every collector already iterates in a fixed, stable order. What the
    explicit sorts in build_graph/to_dict buy is a *canonical* order: nodes by
    (kind, id) and edges by (kind, src, dst), independent of which collector
    ran first. This fixture mixes every node kind and interleaves two edge
    kinds (DERIVED_FROM/DEPENDS_ON both come out of collect_requirements back
    to back) so that collector-insertion order and canonical order are
    visibly different sequences, and pins the canonical one explicitly.
    """
    vault.requirement("REQ-WP-002", depends_on=["REQ-WP-001"])
    vault.requirement("REQ-WP-001")
    vault.decision("ADR-001", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-bootstrap", step="spec", records=["REQ-WP-001"])
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.source("channelflow/bars.py", ["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')

    payload = to_dict(build_graph(vault.root, test_dump=dump))

    # Insertion order (PRD added first, then requirements, outcomes, decisions,
    # specs, code, tests) would start with ("request", "PRD"); canonical order
    # starts with the "code" node, since "code" sorts before "request".
    assert [(n["kind"], n["id"]) for n in payload["nodes"]] == [
        ("code", "src/channelflow/bars.py"),
        ("decision", "ADR-001"),
        ("outcome", "OUT-2026-09-07-spec-bootstrap"),
        ("request", "PRD"),
        ("requirement", "REQ-WP-001"),
        ("requirement", "REQ-WP-002"),
        ("spec", "SPEC-001-bootstrap"),
        ("test", "tests/test_a.py::test_x"),
    ]

    # Insertion order would start with the two DERIVED_FROM edges (both
    # produced before collect_outcomes/collect_decisions run); canonical order
    # starts with DECIDES, since "DECIDES" sorts before "DEPENDS_ON" sorts
    # before "DERIVED_FROM".
    assert [(e["kind"], e["src"], e["dst"]) for e in payload["edges"]] == [
        ("DECIDES", "ADR-001", "REQ-WP-001"),
        ("DEPENDS_ON", "REQ-WP-002", "REQ-WP-001"),
        ("DERIVED_FROM", "REQ-WP-001", "PRD"),
        ("DERIVED_FROM", "REQ-WP-002", "PRD"),
        ("IMPLEMENTS", "src/channelflow/bars.py", "REQ-WP-001"),
        ("RECORDS", "OUT-2026-09-07-spec-bootstrap", "REQ-WP-001"),
        ("SPECIFIES", "SPEC-001-bootstrap", "REQ-WP-001"),
        ("VERIFIES", "tests/test_a.py::test_x", "REQ-WP-001"),
    ]


def test_mermaid_phase_filter_includes_neighbours_and_excludes_other_phases(vault):
    (vault.vault / "10-requirements" / "REQ-PHASE-1A.md").write_text(
        "---\nid: REQ-PHASE-1A\ntitle: Phase one\nstatus: draft\nphase: 1\n---\n\nbody\n"
    )
    (vault.vault / "10-requirements" / "REQ-PHASE-2A.md").write_text(
        "---\nid: REQ-PHASE-2A\ntitle: Phase two\nstatus: draft\nphase: 2\n---\n\nbody\n"
    )
    vault.spec("001-alpha", ["REQ-PHASE-1A"])

    diagram = to_mermaid(build_graph(vault.root), phase=1)

    # The phase-1 requirement and its directly linked spec neighbour are in.
    assert "REQ_PHASE_1A[" in diagram
    assert "SPEC_001_alpha[" in diagram
    # The phase-2 requirement is unrelated to phase 1 and must not appear at
    # all: neither as a node line nor as an edge endpoint.
    assert "REQ_PHASE_2A" not in diagram


def test_mermaid_omits_edges_whose_target_node_does_not_exist(vault):
    """A dangling DEPENDS_ON target can still enter the phase filter's
    neighbour set (the expansion adds edge endpoints without checking they
    are real nodes), so the explicit `if edge.dst not in graph.nodes`
    guard in the edge-rendering loop is what keeps it out of the diagram.
    """
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-404"])

    diagram = to_mermaid(build_graph(vault.root), phase=0)

    assert "REQ_WP_404" not in diagram


def test_mermaid_ids_for_test_nodes_avoid_forbidden_characters(vault, tmp_path):
    vault.requirement("REQ-WP-001")
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')

    diagram = to_mermaid(build_graph(vault.root, test_dump=dump))

    node_line = next(
        line for line in diagram.split("\n") if "tests/test_a.py::test_x" in line
    )
    mermaid_id = node_line.strip().split("[", 1)[0]
    assert not any(forbidden in mermaid_id for forbidden in (":", "/", ".", " "))
