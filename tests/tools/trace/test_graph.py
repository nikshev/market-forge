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
