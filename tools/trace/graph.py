"""Assemble collector output into one graph and export it."""
# @trace: REQ-INFRA-001

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from tools.trace.collect import (
    PRD_NODE_ID,
    collect_code,
    collect_decisions,
    collect_outcomes,
    collect_requirements,
    collect_specs,
    collect_tests,
)
from tools.trace.model import Node, TraceGraph

PRD_FILENAME = "channel_flow_prd_codex_ua_v5.md"

EDGE_ARROWS = {
    "DERIVED_FROM": "-.->",
    "DEPENDS_ON": "-->",
    "SPECIFIES": "==>",
    "VERIFIES": "-->",
    "IMPLEMENTS": "-->",
    "RECORDS": "-.->",
    "DECIDES": "-.->",
}


def build_graph(repo_root: Path, *, test_dump: Path | None = None) -> TraceGraph:
    repo_root = Path(repo_root)
    graph = TraceGraph()
    graph.add(
        Node(
            id=PRD_NODE_ID,
            kind="request",
            path=PRD_FILENAME,
            title="ChannelFlow PRD",
        )
    )

    vault_dir = repo_root / "vault"
    collected = [
        collect_requirements(vault_dir),
        collect_outcomes(vault_dir),
        collect_decisions(vault_dir),
        collect_specs(repo_root / "specs"),
        collect_code([repo_root / "src", repo_root / "tools", repo_root / ".github"]),
        collect_tests(test_dump or repo_root / ".trace" / "tests.json"),
    ]

    for nodes, edges in collected:
        for node in nodes:
            graph.add(node)
        for edge in edges:
            graph.link(edge.src, edge.dst, edge.kind)

    graph.edges.sort(key=lambda e: (e.kind, e.src, e.dst))
    return graph


def to_dict(graph: TraceGraph) -> dict:
    return {
        "nodes": [
            {
                "id": n.id,
                "kind": n.kind,
                "path": n.path,
                "title": n.title,
                "attrs": n.attrs,
            }
            for n in sorted(graph.nodes.values(), key=lambda n: (n.kind, n.id))
        ],
        "edges": [{"src": e.src, "dst": e.dst, "kind": e.kind} for e in graph.edges],
    }


def write_json(graph: TraceGraph, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(graph), indent=2, sort_keys=False) + "\n")


def to_networkx(graph: TraceGraph) -> nx.DiGraph:
    digraph = nx.DiGraph()
    for node in graph.nodes.values():
        digraph.add_node(node.id, kind=node.kind, path=node.path, title=node.title, **node.attrs)
    for edge in graph.edges:
        digraph.add_edge(edge.src, edge.dst, kind=edge.kind)
    return digraph


def _label(node: Node) -> str:
    """Mermaid labels are quoted, so any inner quote must go."""
    text = f"{node.id}" if not node.title else f"{node.id}: {node.title}"
    return text.replace('"', "'").replace("[", "(").replace("]", ")")


def to_mermaid(
    graph: TraceGraph,
    *,
    phase: int | str | None = None,
    exclude_edge_kinds: frozenset[str] = frozenset(),
) -> str:
    if phase is None:
        included = set(graph.nodes)
    else:
        requirements = {
            n.id
            for n in graph.nodes_of_kind("requirement")
            if str(n.attrs.get("phase")) == str(phase)
        }
        included = set(requirements)
        for edge in graph.edges:
            if edge.dst in requirements:
                included.add(edge.src)
            if edge.src in requirements:
                included.add(edge.dst)

    lines = ["```mermaid", "graph LR"]
    for node in sorted(graph.nodes.values(), key=lambda n: (n.kind, n.id)):
        if node.id not in included:
            continue
        lines.append(f'  {_safe(node.id)}["{_label(node)}"]')
    for edge in graph.edges:
        if edge.kind in exclude_edge_kinds:
            continue
        if edge.src not in included or edge.dst not in included:
            continue
        if edge.dst not in graph.nodes:
            continue
        arrow = EDGE_ARROWS.get(edge.kind, "-->")
        lines.append(f"  {_safe(edge.src)} {arrow}|{edge.kind}| {_safe(edge.dst)}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def _safe(node_id: str) -> str:
    """Mermaid node ids may not contain ::, /, . or spaces."""
    return "".join(ch if ch.isalnum() else "_" for ch in node_id)
