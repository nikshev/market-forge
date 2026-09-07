import pytest

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
    assert Violation(
        rule="R1",
        node_id="REQ-WP-001",
        message="status 'specified' requires at least one spec, found none",
    ) in violations


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


# --- R4: outcome recorded ---

def test_r4_fails_when_an_advanced_requirement_has_no_outcome(vault):
    vault.requirement("REQ-WP-001", status="specified")
    vault.spec("001-bootstrap", ["REQ-WP-001"])
    assert "R4" in rules(validate(build_graph(vault.root)))


def test_r4_passes_for_a_draft_requirement(vault):
    vault.requirement("REQ-WP-001", status="draft")
    assert "R4" not in rules(validate(build_graph(vault.root)))


# --- R5: correctness constraints are hard-gated ---

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
