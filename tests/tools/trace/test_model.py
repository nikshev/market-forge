import pytest

from tools.trace.model import Edge, Node, Status, TraceGraph


def test_status_is_ordered():
    assert Status.DRAFT < Status.SPECIFIED < Status.PLANNED
    assert Status.PLANNED < Status.TESTED < Status.IMPLEMENTED < Status.VERIFIED
    # Tasks 8 and 9 gate on >= and > directly, so exercise those operators too.
    assert Status.VERIFIED > Status.IMPLEMENTED
    assert Status.IMPLEMENTED >= Status.IMPLEMENTED
    assert Status.IMPLEMENTED >= Status.TESTED


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("draft", Status.DRAFT),
        ("DRAFT", Status.DRAFT),
        ("  implemented  ", Status.IMPLEMENTED),
        (None, Status.DRAFT),
        ("", Status.DRAFT),
    ],
)
def test_status_parse_normalizes(raw, expected):
    assert Status.parse(raw) is expected


def test_status_parse_rejects_unknown():
    with pytest.raises(ValueError, match="unknown status: 'shipped'"):
        Status.parse("shipped")


def test_nodes_are_hashable_and_frozen():
    node = Node(id="REQ-US-001", kind="requirement", path="vault/10-requirements/REQ-US-001.md")
    assert {node}
    with pytest.raises(AttributeError):
        node.id = "REQ-US-002"


def test_node_attrs_are_excluded_from_equality_and_hash():
    # attrs must not affect compare/hash, or nodes could not stay hashable
    # while carrying a mutable dict.
    a = Node(id="REQ-US-001", kind="requirement", path="a.md", attrs={"owner": "alice"})
    b = Node(id="REQ-US-001", kind="requirement", path="a.md", attrs={"owner": "bob"})
    assert a == b
    assert hash(a) == hash(b)


def test_add_and_lookup_by_kind():
    graph = TraceGraph()
    graph.add(Node(id="REQ-US-001", kind="requirement", path="a.md"))
    graph.add(Node(id="SPEC-001", kind="spec", path="specs/001-x/spec.md"))
    assert [n.id for n in graph.nodes_of_kind("requirement")] == ["REQ-US-001"]
    assert [n.id for n in graph.nodes_of_kind("spec")] == ["SPEC-001"]


def test_add_rejects_duplicate_ids():
    graph = TraceGraph()
    graph.add(Node(id="REQ-US-001", kind="requirement", path="a.md"))
    with pytest.raises(ValueError, match="duplicate node id: 'REQ-US-001'"):
        graph.add(Node(id="REQ-US-001", kind="requirement", path="b.md"))


def test_edges_into_and_out_of_filter_by_kind():
    graph = TraceGraph()
    graph.add(Node(id="REQ-US-001", kind="requirement", path="a.md"))
    graph.add(Node(id="SPEC-001", kind="spec", path="b.md"))
    graph.add(Node(id="t.py::test_x", kind="test", path="t.py"))
    graph.link("SPEC-001", "REQ-US-001", "SPECIFIES")
    graph.link("t.py::test_x", "REQ-US-001", "VERIFIES")

    assert len(graph.edges_into("REQ-US-001")) == 2
    assert graph.edges_into("REQ-US-001", "VERIFIES") == [
        Edge(src="t.py::test_x", dst="REQ-US-001", kind="VERIFIES")
    ]
    assert graph.edges_out_of("SPEC-001", "SPECIFIES")[0].dst == "REQ-US-001"
    assert graph.edges_out_of("REQ-US-001") == []


def test_link_allows_dangling_targets():
    # Dangling references are a validator finding (rule R3), not a crash here.
    graph = TraceGraph()
    graph.add(Node(id="SPEC-001", kind="spec", path="b.md"))
    graph.link("SPEC-001", "REQ-DOES-NOT-EXIST", "SPECIFIES")
    assert graph.edges_of_kind("SPECIFIES")[0].dst == "REQ-DOES-NOT-EXIST"
