"""Coverage rules over a trace graph. Returns findings; never prints or exits."""
# @trace: REQ-INFRA-001

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from tools.trace.model import Status, TraceGraph

# Edge kinds whose destination must be a requirement that exists.
REQUIREMENT_TARGETED = ("SPECIFIES", "VERIFIES", "IMPLEMENTS", "RECORDS", "DECIDES", "DEPENDS_ON")


@dataclass(frozen=True)
class Violation:
    rule: str
    node_id: str
    message: str


def validate(graph: TraceGraph) -> list[Violation]:
    found: list[Violation] = []
    requirements = {n.id: n for n in graph.nodes_of_kind("requirement")}

    for req_id, node in requirements.items():
        status = Status.parse(node.attrs.get("status"))
        hard_gated = bool(node.attrs.get("hard_gated"))
        has_spec = bool(graph.edges_into(req_id, "SPECIFIES"))
        has_test = bool(graph.edges_into(req_id, "VERIFIES"))
        has_outcome = bool(graph.edges_into(req_id, "RECORDS"))
        label = str(status.name).lower()

        if status >= Status.SPECIFIED and not has_spec:
            found.append(
                Violation("R1", req_id, f"status {label!r} requires at least one spec, found none")
            )
        if status >= Status.IMPLEMENTED and not has_test:
            found.append(
                Violation("R2", req_id, f"status {label!r} requires at least one test, found none")
            )
        if status > Status.DRAFT and not has_outcome:
            found.append(
                Violation("R4", req_id, f"status {label!r} requires an outcome note, found none")
            )
        if hard_gated and status > Status.SPECIFIED and not has_test:
            found.append(
                Violation(
                    "R5",
                    req_id,
                    f"hard-gated correctness constraint at {label!r} has no test; PRD "
                    "§13A.28/§41 make this non-waivable",
                )
            )

    for edge in graph.edges:
        if edge.kind in REQUIREMENT_TARGETED and edge.dst not in requirements:
            found.append(
                Violation(
                    "R3",
                    edge.src,
                    f"{edge.kind} points at {edge.dst!r}, which is not a known requirement",
                )
            )

    found.extend(_cycles(graph))
    found.sort(key=lambda v: (v.rule, v.node_id, v.message))
    return found


def _cycles(graph: TraceGraph) -> list[Violation]:
    digraph = nx.DiGraph()
    for edge in graph.edges_of_kind("DEPENDS_ON"):
        digraph.add_edge(edge.src, edge.dst)
    violations: list[Violation] = []
    for cycle in nx.simple_cycles(digraph):
        ordered = sorted(cycle)
        violations.append(
            Violation("R6", ordered[0], "dependency cycle: " + " -> ".join(cycle + [cycle[0]]))
        )
    return violations
