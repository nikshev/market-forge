import pytest

from tools.trace.collect import PRD_NODE_ID
from tools.trace.graph import build_graph
from tools.trace.model import Node, TraceGraph
from tools.trace.validate import Violation, validate


def rules(violations) -> set[str]:
    return {v.rule for v in violations}


# --- R1: spec coverage ---


def test_r1_passes_for_a_draft_requirement_without_a_spec(vault):
    vault.requirement("REQ-WP-001", status="draft")
    assert "R1" not in rules(validate(build_graph(vault.root)))


def test_r1_fails_for_a_specified_requirement_without_a_spec(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-WP-001"])
    violations = validate(build_graph(vault.root))
    assert (
        Violation(
            rule="R1",
            node_id="REQ-WP-001",
            message="status 'specified' requires at least one spec, found none",
        )
        in violations
    )


def test_r1_passes_once_a_spec_traces_it(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-WP-001"])
    assert "R1" not in rules(validate(build_graph(vault.root)))


# --- R2: test coverage ---


def test_r2_fails_for_an_implemented_requirement_without_a_test(vault):
    vault.requirement("REQ-WP-001", status="implemented")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-impl-a", step="implement", records=["REQ-WP-001"])
    assert "R2" in rules(validate(build_graph(vault.root)))


def test_r2_passes_with_a_verifying_test(vault, tmp_path):
    vault.requirement("REQ-WP-001", status="implemented")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-impl-a", step="implement", records=["REQ-WP-001"])
    dump = tmp_path / "tests.json"
    dump.write_text('[{"nodeid": "tests/test_a.py::test_x", "requirements": ["REQ-WP-001"]}]')
    assert "R2" not in rules(validate(build_graph(vault.root, test_dump=dump)))


# --- R3: dangling references ---


def test_r3_fails_on_a_spec_tracing_an_unknown_requirement(vault):
    vault.spec("001-bootstrap", ["REQ-WP-999"])
    violations = validate(build_graph(vault.root))
    assert any(v.rule == "R3" and "REQ-WP-999" in v.message for v in violations)


def test_r3_fails_on_a_depends_on_pointing_nowhere(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-404"])
    violations = validate(build_graph(vault.root))
    assert any(v.rule == "R3" and "REQ-WP-404" in v.message for v in violations)


def test_r3_passes_when_every_reference_resolves(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002")
    assert "R3" not in rules(validate(build_graph(vault.root)))


@pytest.mark.parametrize(
    "kind",
    ["DEPENDS_ON", "SPECIFIES", "VERIFIES", "IMPLEMENTS", "RECORDS", "DECIDES"],
)
def test_r3_fires_for_every_requirement_targeted_kind(kind):
    """Pins REQUIREMENT_TARGETED itself, not just the branch that reads it.

    If a kind were ever dropped from that tuple, this conditional would still
    be "correct" and R3 would silently stop checking it.
    """
    graph = TraceGraph()
    graph.add(Node(id="REQ-WP-001", kind="requirement", path="a.md"))
    graph.link("REQ-WP-001", "REQ-WP-999", kind)
    violations = validate(graph)
    assert any(v.rule == "R3" and "REQ-WP-999" in v.message for v in violations)


def test_r3_ignores_derived_from_edges_to_the_prd(vault):
    """Every requirement carries a DERIVED_FROM edge to PRD, a non-requirement
    node. If DERIVED_FROM were ever added to REQUIREMENT_TARGETED, every
    requirement in the project would trip R3 at once.
    """
    vault.requirement("REQ-WP-001")
    assert "R3" not in rules(validate(build_graph(vault.root)))
    graph = build_graph(vault.root)
    assert any(
        e.src == "REQ-WP-001" and e.dst == PRD_NODE_ID and e.kind == "DERIVED_FROM"
        for e in graph.edges
    )


# --- R4: outcome recorded ---


def test_r4_fails_when_an_advanced_requirement_has_no_outcome(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    assert "R4" in rules(validate(build_graph(vault.root)))


def test_r4_passes_for_a_draft_requirement(vault):
    vault.requirement("REQ-WP-001", status="draft")
    assert "R4" not in rules(validate(build_graph(vault.root)))


# --- R5: correctness constraints are hard-gated ---


@pytest.mark.trace("REQ-INFRA-001")
def test_r5_fails_for_a_planned_constraint_without_a_test(vault):
    """R5 bites where R2 does not: 'planned' is below 'implemented'."""
    vault.requirement("REQ-BIAS-002", status="planned", type_="constraint")
    vault.spec("001-no-centered-filters", ["REQ-BIAS-002"])
    vault.outcome("OUT-2026-09-07-plan-a", step="plan", records=["REQ-BIAS-002"])
    violations = validate(build_graph(vault.root))
    assert "R5" in rules(violations)
    assert "R2" not in rules(violations)


def test_r5_passes_for_a_specified_constraint_without_a_test(vault):
    vault.requirement("REQ-BIAS-002", status="specified", type_="constraint")
    vault.spec("001-no-centered-filters", ["REQ-BIAS-002"])
    vault.outcome("OUT-2026-09-07-spec-a", step="spec", records=["REQ-BIAS-002"])
    assert "R5" not in rules(validate(build_graph(vault.root)))


def test_r5_ignores_non_constraint_types(vault):
    vault.requirement("REQ-WP-001", status="planned", type_="work-package")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    vault.outcome("OUT-2026-09-07-plan-a", step="plan", records=["REQ-WP-001"])
    assert "R5" not in rules(validate(build_graph(vault.root)))


# --- R6: dependency cycles ---


def test_r6_detects_a_two_node_cycle(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002", depends_on=["REQ-WP-001"])
    violations = validate(build_graph(vault.root))
    assert "R6" in rules(violations)
    assert any("REQ-WP-001" in v.message and "REQ-WP-002" in v.message for v in violations)


def test_r6_passes_on_a_chain(vault):
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-002"])
    vault.requirement("REQ-WP-002", depends_on=["REQ-WP-003"])
    vault.requirement("REQ-WP-003")
    assert "R6" not in rules(validate(build_graph(vault.root)))


def test_r6_detects_a_self_loop(vault):
    """A requirement depending on itself is a one-node cycle. This must not
    rely solely on the third-party detail that nx.simple_cycles reports
    self-edges; the message must name the requirement on both sides so a
    truncated report (e.g. a bare "REQ-WP-001") cannot pass silently.
    """
    vault.requirement("REQ-WP-001", depends_on=["REQ-WP-001"])
    violations = validate(build_graph(vault.root))
    assert "R6" in rules(violations)
    assert any(v.rule == "R6" and v.message.count("REQ-WP-001") >= 2 for v in violations)


# --- R7: unique ids ---


def test_r7_is_raised_by_the_graph_itself(vault):
    graph = TraceGraph()
    graph.add(Node(id="REQ-WP-001", kind="requirement", path="a.md"))
    with pytest.raises(ValueError, match="duplicate node id"):
        graph.add(Node(id="REQ-WP-001", kind="requirement", path="b.md"))


# --- ordering ---


def test_violations_are_sorted_by_rule_then_node(vault):
    vault.requirement("REQ-WP-002", status="specified")
    vault.requirement("REQ-WP-001", status="specified")
    violations = validate(build_graph(vault.root))
    keys = [(v.rule, v.node_id) for v in violations]
    assert keys == sorted(keys)
