from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    shape: str = "box"
    role: str | None = None


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    label: str | None = None
    directed: bool = True
    style: str = "solid"


@dataclass(frozen=True)
class DiagramIR:
    family: str
    direction: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    schema_version: str = "1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "family": self.family,
            "direction": self.direction,
            "nodes": [
                {"id": n.id, "label": n.label, "shape": n.shape, **({"role": n.role} if n.role else {})}
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    **({"label": e.label} if e.label is not None else {}),
                    "directed": e.directed,
                    "style": e.style,
                }
                for e in self.edges
            ],
        }


@dataclass(frozen=True)
class ArtifactBundle:
    path: Any
    artifacts: tuple[Any, ...] = field(default_factory=tuple)
