"""Coverage rules over a trace graph. Returns findings; never prints or exits."""
# @trace: REQ-INFRA-001

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from tools.trace.model import Status, TraceGraph

# Edge kinds whose destination must be a requirement that exists.
REQUIREMENT_TARGETED = (
    "SPECIFIES",
    "VERIFIES",
    "IMPLEMENTS",
    "RECORDS",
    "DECIDES",
    "DEPENDS_ON",
    "COVERS",
)


@dataclass(frozen=True)
class Violation:
    rule: str
    node_id: str
    message: str


def _has_code(graph: TraceGraph, req_id: str) -> bool:
    """Whether anything traceable implements this requirement.

    Directly, for a requirement code can carry the marker of. Through its
    `covers:` list for one that nothing can: a phase is a roll-up of PRD §45's
    deliverables, and no module implements a phase -- it implements a work
    package that delivers part of one.

    R8 was written before any phase left `draft`, so this case had never come
    up: under the direct reading a phase can never be `implemented`, which makes
    the top of the ladder unreachable for a whole requirement type rather than
    merely unearned. Following `covers:` keeps the rule's meaning -- implemented
    means code exists -- and makes it answerable for a roll-up. A phase that
    covers nothing still has no code, which is the right answer for one.
    """
    if graph.edges_into(req_id, "IMPLEMENTS"):
        return True
    covered = [edge.dst for edge in graph.edges_out_of(req_id, "COVERS")]
    return bool(covered) and all(graph.edges_into(dst, "IMPLEMENTS") for dst in covered)


def validate(graph: TraceGraph) -> list[Violation]:
    found: list[Violation] = []
    requirements = {n.id: n for n in graph.nodes_of_kind("requirement")}

    for req_id, node in requirements.items():
        status = Status.parse(node.attrs.get("status"))
        hard_gated = bool(node.attrs.get("hard_gated"))
        has_spec = bool(graph.edges_into(req_id, "SPECIFIES"))
        has_test = bool(graph.edges_into(req_id, "VERIFIES"))
        has_outcome = bool(graph.edges_into(req_id, "RECORDS"))
        has_code = _has_code(graph, req_id)
        label = str(status.name).lower()

        if status >= Status.SPECIFIED and not has_spec:
            found.append(
                Violation("R1", req_id, f"status {label!r} requires at least one spec, found none")
            )
        if status >= Status.IMPLEMENTED and not has_test:
            found.append(
                Violation("R2", req_id, f"status {label!r} requires at least one test, found none")
            )
        # R8. Found by REQ-WP-010: a requirement marked implemented, with a
        # full test suite and no `# @trace:` marker in any source file,
        # validated clean. R2 asks whether tests exist, not whether anything
        # they test is traceable -- so the request-to-implementation half of
        # the graph could be empty and the gate would still say so.
        if status >= Status.IMPLEMENTED and not has_code:
            found.append(
                Violation(
                    "R8",
                    req_id,
                    f"status {label!r} requires at least one source file carrying "
                    "`# @trace: <id>`, found none",
                )
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
