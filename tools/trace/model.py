"""Value types for the traceability graph. No I/O lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Status(IntEnum):
    """The requirement lifecycle, ordered so comparisons express the ladder."""

    DRAFT = 0
    SPECIFIED = 1
    PLANNED = 2
    TESTED = 3
    IMPLEMENTED = 4
    VERIFIED = 5

    @classmethod
    def parse(cls, raw: str | None) -> Status:
        if raw is None or not str(raw).strip():
            return cls.DRAFT
        key = str(raw).strip().upper()
        try:
            return cls[key]
        except KeyError:
            raise ValueError(f"unknown status: {str(raw).strip()!r}") from None


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    path: str
    title: str = ""
    attrs: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str


@dataclass
class TraceGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"duplicate node id: {node.id!r}")
        self.nodes[node.id] = node

    def link(self, src: str, dst: str, kind: str) -> None:
        """Record an edge. Targets need not exist; rule R3 reports dangling ones."""
        self.edges.append(Edge(src=src, dst=dst, kind=kind))

    def nodes_of_kind(self, kind: str) -> list[Node]:
        return [n for n in self.nodes.values() if n.kind == kind]

    def edges_of_kind(self, kind: str) -> list[Edge]:
        return [e for e in self.edges if e.kind == kind]

    def edges_into(self, node_id: str, kind: str | None = None) -> list[Edge]:
        return [e for e in self.edges if e.dst == node_id and (kind is None or e.kind == kind)]

    def edges_out_of(self, node_id: str, kind: str | None = None) -> list[Edge]:
        return [e for e in self.edges if e.src == node_id and (kind is None or e.kind == kind)]
